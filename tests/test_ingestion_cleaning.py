from __future__ import annotations

from dataclasses import asdict, replace
from datetime import UTC, datetime

from core.utils import write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records, parse_crossref_payload


def _payload() -> dict:
    return {
        "message": {
            "items": [
                {
                    "DOI": "10.1234/ABC",
                    "title": ["  A   Test Paper  "],
                    "abstract": "<jats:p>An &amp; abstract with <b>markup</b>.</jats:p>",
                    "author": [{"given": "Chi", "family": "Hieu"}],
                    "subject": [],
                    "type": "journal-article",
                    "published": {"date-parts": [[2026, 7]]},
                    "indexed": {"date-time": "2026-08-01T12:00:00Z"},
                    "URL": "https://doi.org/10.1234/ABC",
                    "link": [
                        {
                            "content-type": "application/pdf",
                            "URL": "https://example.org/paper.pdf",
                        }
                    ],
                },
                {"DOI": "10.1234/abc", "title": ["Duplicate"]},
            ]
        }
    }


def test_parse_and_load_crossref_records(tmp_path):
    records = parse_crossref_payload(_payload())

    assert len(records) == 1
    assert records[0].paper_id == "10.1234/abc"
    assert records[0].title == "A Test Paper"
    assert records[0].summary == "An & abstract with markup."
    assert records[0].authors == ["Chi Hieu"]
    assert records[0].categories == ["journal-article"]
    assert records[0].published == "2026-07-01"
    assert records[0].updated == "2026-08-01"
    assert records[0].pdf_url == "https://example.org/paper.pdf"

    snapshot = tmp_path / "crossref_records.json"
    write_json(snapshot, [asdict(record) for record in records])
    assert load_raw_records(snapshot) == records


def test_clean_dataframe_filters_deduplicates_and_tracks_reasons():
    parsed = parse_crossref_payload(_payload())[0]
    valid = replace(
        parsed,
        summary=(
            "This sufficiently long abstract describes a reproducible retrieval system, "
            "its data processing stages, evaluation design, and measured outcomes."
        ),
    )
    short_summary = replace(
        parsed,
        paper_id="10.1234/short",
        title="Short summary",
        summary="Too short for the required clean-data contract.",
    )

    dataframe = build_clean_dataframe(
        [valid, valid, short_summary],
        run_date=datetime(2026, 8, 6, tzinfo=UTC),
    )

    assert len(dataframe) == 1
    assert dataframe.iloc[0]["age_days"] == 36
    assert dataframe.iloc[0]["summary_chars"] == len(valid.summary)
    assert dataframe.iloc[0]["text_for_embedding"] == (
        f"Title: {valid.title} | Authors: Chi Hieu | Summary: {valid.summary}"
    )
    summary = dataframe.attrs["cleaning_summary"]
    assert summary["input_records"] == 3
    assert summary["output_records"] == 1
    assert summary["drop_reasons"]["duplicate_paper_id"] == 1
    assert summary["drop_reasons"]["summary_too_short"] == 1
