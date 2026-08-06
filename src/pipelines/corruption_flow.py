from __future__ import annotations

import pandas as pd

from core.config import Paths, Settings, load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.repair import repair_corrupted_dataframe
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _load_clean_df(settings: Settings) -> pd.DataFrame:
    """Load the committed baseline used as the trusted good-data reference."""
    if not settings.paths.clean_json.exists():
        raise RuntimeError(
            f"Missing good baseline data at {settings.paths.clean_json}. Run pipelines.phase1 first."
        )
    return pd.DataFrame(read_json(settings.paths.clean_json))


def _evaluate_state(
    settings: Settings,
    df: pd.DataFrame,
    embeddings_path,
    metrics_path,
    answers_path,
) -> dict[str, object]:
    index = LocalEmbeddingIndex.build(
        df=df,
        settings=settings,
        embeddings_output_path=embeddings_path,
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
    5. Repair only logged corruptions by pulling values from good baseline data.
    6. Evaluate repaired data.
    7. Run quality & freshness checks on repaired data.
    8. Write comparison report.
    """
    settings = load_settings()
    paths: Paths = settings.paths

    if not paths.baseline_metrics.exists():
        raise RuntimeError(
            f"Missing baseline metrics at {paths.baseline_metrics}. Run pipelines.phase1 first."
        )
    if not paths.eval_testset.exists():
        raise RuntimeError(
            f"Missing evaluation test set at {paths.eval_testset}. Run pipelines.phase1 first."
        )

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
        paths.corrupted_embeddings_json,
        paths.corrupted_metrics,
        paths.corrupted_answers,
    )

    # ---- 4. Quality & freshness (corrupted) --------------------------------
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, paths.corrupted_freshness_report
    )

    # ---- 5. Repair ---------------------------------------------------------
    repaired_df, repair_log = repair_corrupted_dataframe(
        corrupted=corrupted_df,
        good=clean_df,
        corruption_log=read_json(paths.corruption_log),
    )
    write_csv(repaired_df, paths.repaired_clean_csv)
    write_json(paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    write_json(paths.repair_log, repair_log)
    print(f"Repaired data: {len(repaired_df)} rows")

    # ---- 6. Evaluate repaired ----------------------------------------------
    print("Evaluating repaired state ...")
    repaired_summary = _evaluate_state(
        settings,
        repaired_df,
        paths.repaired_embeddings_json,
        paths.repaired_metrics,
        paths.repaired_answers,
    )

    # ---- 7. Quality & freshness (repaired) ---------------------------------
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, paths.repaired_freshness_report
    )

    # ---- 8. Load baseline metrics for comparison ---------------------------
    baseline_metrics = read_json(paths.baseline_metrics)

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

    print("Corruption flow complete.")
    print(f"   Corrupted data:  {paths.corrupted_clean_csv}")
    print(f"   Corrupted metrics: {paths.corrupted_metrics}")
    print(f"   Repaired metrics:  {paths.repaired_metrics}")
    print(f"   Repair log:        {paths.repair_log}")
    print(f"   Report:            {paths.comparison_report}")


if __name__ == "__main__":
    main()
