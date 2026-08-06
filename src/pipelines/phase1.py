from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from core.config import Paths, Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Run the baseline pipeline end-to-end.

    Steps
    -----
    1. Load settings from ``.env``.
    2. Load (or fetch) raw Crossref records.
    3. Clean records → DataFrame.
    4. Persist clean CSV & JSON.
    5. Build (or load cached) ChromaDB embedding index.
    6. Build (or load cached) evaluation test set.
    7. Evaluate retrieval + answer quality.
    8. Run data-quality checks and freshness report.
    9. Write the Phase-1 Markdown report.
    """
    settings = load_settings()
    paths: Paths = settings.paths
    run_date = now_utc()

    # ---- 2. Raw records ----------------------------------------------------
    if settings.refresh_source or not paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(paths.raw_records_json)

    # ---- 3. Clean ----------------------------------------------------------
    clean_df: pd.DataFrame = build_clean_dataframe(records, run_date)
    if clean_df.empty:
        raise RuntimeError("Cleaning produced an empty DataFrame — cannot continue.")

    # ---- 4. Persist clean artifacts ----------------------------------------
    write_csv(clean_df, paths.clean_csv)
    write_json(paths.clean_json, clean_df.to_dict(orient="records"))

    # ---- 5. Embedding index ------------------------------------------------
    index = LocalEmbeddingIndex.build(df=clean_df, settings=settings)

    # ---- 6. Evaluation test set --------------------------------------------
    if settings.refresh_test_set or not paths.eval_testset.exists():
        build_test_set(clean_df, paths.eval_testset)

    # ---- 7. Evaluate -------------------------------------------------------
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )

    # ---- 8. Quality & freshness --------------------------------------------
    quality = run_data_quality_checks(clean_df, settings, "baseline")
    freshness = build_freshness_report(clean_df, settings, paths.freshness_report)

    # ---- 9. Baseline report ------------------------------------------------
    source_summary = (
        read_json(paths.raw_api_response.parent / "source_manifest.json")
        if (paths.raw_api_response.parent / "source_manifest.json").exists()
        else {"source": "Crossref REST API", "query": settings.source_query}
    )
    generate_phase1_report(
        report_path=paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality,
        freshness=freshness,
    )

    print(f"✅ Baseline pipeline complete.")
    print(f"   Clean records:  {len(clean_df)}")
    print(f"   Metrics:        {paths.baseline_metrics}")
    print(f"   Answers:        {paths.baseline_answers}")
    print(f"   Quality:        {paths.quality_dir}")
    print(f"   Freshness:      {paths.freshness_report}")
    print(f"   Report:         {paths.baseline_report}")
