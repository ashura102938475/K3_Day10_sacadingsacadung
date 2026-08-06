from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from core.config import load_settings
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import PaperRecord
from observability.quality import run_data_quality_checks
from ingestion.repair import repair_corrupted_dataframe
from core.utils import read_json


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


def test_repair_targets_only_logged_corruptions(tmp_path):
    clean = build_clean_dataframe(_records(), datetime(2026, 8, 6, tzinfo=UTC))
    log_path = tmp_path / "corruption_log.json"
    corrupted = corrupt_clean_dataframe(clean, log_path)

    repaired, repair_log = repair_corrupted_dataframe(corrupted, clean, read_json(log_path))

    assert len(repaired) == len(clean)
    assert repaired["paper_id"].is_unique
    assert set(repaired["paper_id"]) == set(clean["paper_id"])
    assert repaired.to_dict(orient="records") == clean.to_dict(orient="records")
    assert repair_log["targeted_unique_records"] < len(clean)
    assert repair_log["unaffected_reference_records"] > 0


def test_repair_preserves_unlogged_fields_on_unaffected_records(tmp_path):
    clean = build_clean_dataframe(_records(), datetime(2026, 8, 6, tzinfo=UTC))
    log_path = tmp_path / "corruption_log.json"
    corrupted = corrupt_clean_dataframe(clean, log_path)
    corruption_log = read_json(log_path)
    targeted_ids = {
        str(paper_id)
        for entry in corruption_log["entries"]
        for paper_id in entry["affected_paper_ids"]
    }
    unaffected_id = next(
        paper_id for paper_id in corrupted["paper_id"] if paper_id not in targeted_ids
    )
    corrupted.loc[corrupted["paper_id"].eq(unaffected_id), "comment"] = "keep this annotation"

    repaired, _ = repair_corrupted_dataframe(corrupted, clean, corruption_log)

    repaired_comment = repaired.loc[repaired["paper_id"].eq(unaffected_id), "comment"].iloc[0]
    assert repaired_comment == "keep this annotation"
