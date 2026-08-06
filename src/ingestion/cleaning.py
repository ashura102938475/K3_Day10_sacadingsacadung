from __future__ import annotations

from datetime import date, datetime
from html import unescape
import re
from typing import Any, Iterable

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "abs_url",
    "pdf_url",
    "comment",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "age_days",
    "text_for_embedding",
]


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    normalized = normalize_whitespace(_HTML_TAG_RE.sub(" ", unescape(str(value))))
    return re.sub(r"\s+([,.;:!?])", r"\1", normalized)


def _clean_list(values: Iterable[Any] | None) -> list[str]:
    if values is None or isinstance(values, (str, bytes)):
        return []

    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = _clean_text(value)
        key = item.casefold()
        if item and key not in seen:
            cleaned.append(item)
            seen.add(key)
    return cleaned


def _parse_date(value: Any) -> date | None:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    return parsed.date()


def _embedding_text(
    title: str,
    summary: str,
    authors_joined: str,
    categories_joined: str,
    published: str,
) -> str:
    parts = [f"Title: {title}", f"Abstract: {summary}"]
    if authors_joined:
        parts.append(f"Authors: {authors_joined}")
    if categories_joined:
        parts.append(f"Categories: {categories_joined}")
    parts.append(f"Published: {published}")
    return "\n".join(parts)


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize raw records into the stable dataframe contract used downstream."""
    run_day = run_date.date()
    drop_counts = {
        "missing_paper_id": 0,
        "missing_title": 0,
        "missing_summary": 0,
        "invalid_published": 0,
        "duplicate_paper_id": 0,
    }
    rows: list[dict[str, Any]] = []

    for record in records:
        paper_id = _clean_text(record.paper_id).lower()
        title = _clean_text(record.title)
        summary = _clean_text(record.summary)
        published_date = _parse_date(record.published)

        if not paper_id:
            drop_counts["missing_paper_id"] += 1
            continue
        if not title:
            drop_counts["missing_title"] += 1
            continue
        if not summary:
            drop_counts["missing_summary"] += 1
            continue
        if published_date is None:
            drop_counts["invalid_published"] += 1
            continue

        authors = _clean_list(record.authors)
        categories = _clean_list(record.categories)
        primary_category = _clean_text(record.primary_category)
        if not primary_category and categories:
            primary_category = categories[0]
        updated_date = _parse_date(record.updated)
        published = published_date.isoformat()
        updated = updated_date.isoformat() if updated_date else ""
        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "abs_url": _clean_text(record.abs_url),
                "pdf_url": _clean_text(record.pdf_url),
                "comment": _clean_text(record.comment),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "age_days": (run_day - published_date).days,
                "text_for_embedding": _embedding_text(
                    title,
                    summary,
                    authors_joined,
                    categories_joined,
                    published,
                ),
            }
        )

    dataframe = pd.DataFrame(rows, columns=_CLEAN_COLUMNS)
    if dataframe.empty:
        dataframe.attrs["cleaning_summary"] = {
            "input_records": len(records),
            "output_records": 0,
            "dropped_records": sum(drop_counts.values()),
            "drop_reasons": drop_counts,
        }
        return dataframe

    duplicate_mask = dataframe.duplicated(subset=["paper_id"], keep="first")
    drop_counts["duplicate_paper_id"] = int(duplicate_mask.sum())
    dataframe = dataframe.loc[~duplicate_mask].copy()
    dataframe = dataframe.sort_values(
        by=["published", "paper_id"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)
    dataframe.attrs["cleaning_summary"] = {
        "input_records": len(records),
        "output_records": len(dataframe),
        "dropped_records": len(records) - len(dataframe),
        "drop_reasons": drop_counts,
    }
    return dataframe
