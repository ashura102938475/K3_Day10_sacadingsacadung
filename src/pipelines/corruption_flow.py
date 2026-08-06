from __future__ import annotations

import pandas as pd

from core.config import Paths, Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _load_clean_df(settings: Settings) -> pd.DataFrame:
    """Load the existing clean CSV or rebuild from raw records."""
    if settings.paths.clean_csv.exists():
        return pd.read_csv(settings.paths.clean_csv)
    records = load_raw_records(settings.paths.raw_records_json)
    return build_clean_dataframe(records, now_utc())


def _repair_from_raw(settings: Settings, corrupted: pd.DataFrame) -> pd.DataFrame:
    """Repair the corrupted DataFrame by restoring data from raw records.

    The repair strategy:
    - Reload trusted raw records.
    - Rebuild the clean DataFrame from scratch.
    - Keep only the paper_ids that are present in the corrupted set
      (so the row count stays comparable).
    """
    records = load_raw_records(settings.paths.raw_records_json)
    clean_df = build_clean_dataframe(records, now_utc())
    corrupted_ids = set(corrupted["paper_id"].astype(str).str.lower())
    repaired = clean_df[clean_df["paper_id"].str.lower().isin(corrupted_ids)].copy()
    if repaired.empty:
        # Fallback: return a fresh clean build.
        return clean_df
    return repaired.reset_index(drop=True)


def _evaluate_state(
    settings: Settings,
    df: pd.DataFrame,
    collection_name: str,
    metrics_path,
    answers_path,
) -> dict[str, object]:
    index = LocalEmbeddingIndex.build(df=df, settings=settings)
    # Override collection name for isolation.
    index = LocalEmbeddingIndex(
        settings=settings,
        collection_name=collection_name,
        documents=index.documents,
        persist_path=settings.paths.chroma_dir,
    )
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=metrics_path,
        answers_output_path=answers_path,
    )
    return bundle.summary


def main() -> None:
    """Run the corruption → evaluate → repair → compare flow.

    Steps
    -----
    1. Load baseline clean DataFrame.
    2. Apply corruptions and save corrupted artifacts.
    3. Rebuild index over corrupted data and evaluate.
    4. Run quality & freshness checks on corrupted data.
    5. Repair corrupted data from raw source records.
    6. Evaluate repaired data.
    7. Run quality & freshness checks on repaired data.
    8. Write comparison report.
    """
    settings = load_settings()
    paths: Paths = settings.paths

    # ---- 1. Load clean data ------------------------------------------------
    clean_df = _load_clean_df(settings)
    print(f"Loaded clean data: {len(clean_df)} rows")

    # ---- 2. Corrupt --------------------------------------------------------
    corrupted_df = corrupt_clean_dataframe(clean_df, paths.corruption_log)
    write_csv(corrupted_df, paths.corrupted_clean_csv)
    write_json(paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    print(f"Corrupted data: {len(corrupted_df)} rows (was {len(clean_df)})")

    # ---- 3. Evaluate corrupted ---------------------------------------------
    print("Evaluating corrupted state ...")
    corrupted_summary = _evaluate_state(
        settings,
        corrupted_df,
        settings.corrupted_collection_name,
        paths.corrupted_metrics,
        paths.corrupted_answers,
    )

    # ---- 4. Quality & freshness (corrupted) --------------------------------
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, paths.freshness_report
    )

    # ---- 5. Repair ---------------------------------------------------------
    repaired_df = _repair_from_raw(settings, corrupted_df)
    write_csv(repaired_df, paths.repaired_clean_csv)
    write_json(paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    print(f"Repaired data: {len(repaired_df)} rows")

    # ---- 6. Evaluate repaired ----------------------------------------------
    print("Evaluating repaired state ...")
    repaired_summary = _evaluate_state(
        settings,
        repaired_df,
        settings.repaired_collection_name,
        paths.repaired_metrics,
        paths.repaired_answers,
    )

    # ---- 7. Quality & freshness (repaired) ---------------------------------
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, paths.freshness_report
    )

    # ---- 8. Load baseline metrics for comparison ---------------------------
    baseline_metrics = (
        read_json(paths.baseline_metrics)
        if paths.baseline_metrics.exists()
        else corrupted_summary
    )

    # ---- 9. Comparison report ----------------------------------------------
    generate_corruption_report(
        report_path=paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_summary,
        repaired_metrics=repaired_summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    print(f"✅ Corruption flow complete.")
    print(f"   Corrupted data:  {paths.corrupted_clean_csv}")
    print(f"   Corrupted metrics: {paths.corrupted_metrics}")
    print(f"   Repaired metrics:  {paths.repaired_metrics}")
    print(f"   Report:            {paths.comparison_report}")
