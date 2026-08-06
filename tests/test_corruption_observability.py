from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from core.config import load_settings
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import PaperRecord
from observability.quality import run_data_quality_checks
from pipelines.corruption_flow import _repair_from_raw
from core.utils import write_json


def _records(count: int = 12) -> list[PaperRecord]:
    return [
        PaperRecord(
            paper_id=f"10.1234/paper-{index:02d}",
            title=f"Reliable retrieval paper number {index:02d}",
            summary=(
                "This reproducible abstract describes retrieval, data cleaning, "
                "evaluation, observability, and measured outcomes in sufficient detail. "
                f"Record {index}."
            ),
            authors=[f"Author {index}"],
            categories=["journal-article"],
            primary_category="journal-article",
            published=f"2026-07-{index:02d}",
            updated="2026-08-01",
            abs_url=f"https://doi.org/10.1234/paper-{index:02d}",
            pdf_url="",
            comment="",
        )
        for index in range(1, count + 1)
    ]


def test_corruption_is_detected_without_accidental_embedding_mismatches(tmp_path):
    settings = load_settings()
    settings = replace(
        settings,
        paths=replace(settings.paths, quality_dir=tmp_path / "quality"),
    )
    clean = build_clean_dataframe(_records(), datetime(2026, 8, 6, tzinfo=UTC))

    corrupted = corrupt_clean_dataframe(clean, tmp_path / "corruption_log.json")
    report = run_data_quality_checks(corrupted, settings, "corrupted")
    checks = {item["check"]: item for item in report["checks"]}

    assert len(corrupted) == len(clean)
    assert corrupted["paper_id"].nunique() == len(clean) - 2
    assert checks["paper_id_unique"]["passed"] is False
    assert checks["summary_min_length"]["passed"] is False
    assert checks["title_not_truncated"]["passed"] is False
    assert checks["text_for_embedding_has_no_noise_tokens"]["passed"] is False
    assert checks["text_for_embedding_matches_source_fields"]["passed"] is True


def test_repair_restores_records_dropped_by_corruption(tmp_path):
    settings = load_settings()
    raw_path = tmp_path / "crossref_records.json"
    write_json(raw_path, [record.__dict__ for record in _records()])
    settings = replace(
        settings,
        paths=replace(settings.paths, raw_records_json=raw_path),
    )
    clean = build_clean_dataframe(_records(), datetime(2026, 8, 6, tzinfo=UTC))
    corrupted = corrupt_clean_dataframe(clean, tmp_path / "corruption_log.json")

    repaired = _repair_from_raw(settings, corrupted)

    assert len(repaired) == len(clean)
    assert repaired["paper_id"].is_unique
    assert set(repaired["paper_id"]) == set(clean["paper_id"])
