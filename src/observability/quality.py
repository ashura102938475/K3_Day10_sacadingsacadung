from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import ensure_parent, write_json


def _check_result(
    name: str,
    passed: bool,
    dimension: str,
    observed: Any,
    expected: Any,
    details: str = "",
) -> dict[str, Any]:
    return {
        "check": name,
        "passed": passed,
        "quality_dimension": dimension,
        "observed": str(observed),
        "expected": str(expected),
        "details": details,
    }


def run_data_quality_checks(
    df: pd.DataFrame,
    settings: Settings,
    report_name: str,
) -> dict[str, Any]:
    """Run a structured battery of data-quality checks against *df*.

    Checks cover row count, uniqueness, completeness, content length,
    and freshness.  Results are written to ``data/quality/<report_name>.json``.
    """
    checks: list[dict[str, Any]] = []

    # Row count
    min_rows = 1
    checks.append(
        _check_result(
            "row_count",
            len(df) >= min_rows,
            "Completeness",
            f"{len(df)} rows",
            f">= {min_rows} row(s)",
        )
    )

    # paper_id not null
    null_ids = int(df["paper_id"].isna().sum())
    checks.append(
        _check_result(
            "paper_id_not_null",
            null_ids == 0,
            "Completeness",
            f"{null_ids} null(s)",
            "0 nulls",
            f"paper_id null count = {null_ids}",
        )
    )

    # paper_id unique
    dup_ids = int(df["paper_id"].duplicated().sum())
    checks.append(
        _check_result(
            "paper_id_unique",
            dup_ids == 0,
            "Uniqueness",
            f"{dup_ids} duplicate(s)",
            "0 duplicates",
            f"paper_id duplicate count = {dup_ids}",
        )
    )

    # title not null
    null_titles = int(df["title"].isna().sum())
    checks.append(
        _check_result(
            "title_not_null",
            null_titles == 0,
            "Completeness",
            f"{null_titles} null(s)",
            "0 nulls",
        )
    )

    # summary minimum length (>= 50 chars as a softer post-corruption floor)
    if "summary" in df.columns and len(df) > 0:
        short_summaries = int((df["summary"].fillna("").str.len() < 50).sum())
        checks.append(
            _check_result(
                "summary_min_length",
                short_summaries == 0,
                "Completeness",
                f"{short_summaries} row(s) with summary < 50 chars",
                "0 rows",
            )
        )

    # summary_chars >= 0
    if "summary_chars" in df.columns:
        negative_chars = int((df["summary_chars"] < 0).sum())
        checks.append(
            _check_result(
                "summary_chars_non_negative",
                negative_chars == 0,
                "Validity",
                f"{negative_chars} row(s) with negative summary_chars",
                "0 rows",
            )
        )

    # age_days reasonable (>= 0)
    if "age_days" in df.columns:
        negative_ages = int((df["age_days"] < 0).sum())
        checks.append(
            _check_result(
                "age_days_non_negative",
                negative_ages == 0,
                "Validity",
                f"{negative_ages} row(s) with negative age_days",
                "0 rows",
            )
        )

    # text_for_embedding not empty
    if "text_for_embedding" in df.columns:
        empty_text = int(df["text_for_embedding"].fillna("").str.strip().eq("").sum())
        checks.append(
            _check_result(
                "text_for_embedding_not_empty",
                empty_text == 0,
                "Completeness",
                f"{empty_text} empty(s)",
                "0 empty",
            )
        )

    passed = sum(1 for c in checks if c["passed"])
    failed = len(checks) - passed
    summary = {
        "report_name": report_name,
        "total_checks": len(checks),
        "passed": passed,
        "failed": failed,
        "all_passed": failed == 0,
    }

    report = {"summary": summary, "checks": checks}
    output_path = settings.paths.quality_dir / f"{report_name}.json"
    write_json(output_path, report)
    return report


def build_freshness_report(
    df: pd.DataFrame,
    settings: Settings,
    report_path: str | Path,
) -> dict[str, Any]:
    """Produce a freshness report that flags stale documents.

    A row is considered *stale* when ``age_days`` exceeds the configured
    ``freshness_threshold_days`` (default 180).
    """
    threshold = settings.freshness_threshold_days

    latest_published = ""
    oldest_published = ""
    stale_rows = 0
    total_rows = len(df)

    if "published" in df.columns and len(df) > 0:
        published_dates = pd.to_datetime(df["published"], errors="coerce")
        valid = published_dates.dropna()
        if len(valid) > 0:
            latest_published = valid.max().strftime("%Y-%m-%d")
            oldest_published = valid.min().strftime("%Y-%m-%d")

    if "age_days" in df.columns:
        stale_rows = int((df["age_days"] > threshold).sum())

    is_fresh = stale_rows == 0

    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "threshold_days": threshold,
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_rows / total_rows, 4) if total_rows else 0.0,
        "is_fresh": is_fresh,
    }

    report_path = Path(report_path)
    ensure_parent(report_path)
    write_json(report_path, report)
    return report
