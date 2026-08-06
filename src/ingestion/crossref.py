from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import UTC, date, datetime
from html import unescape
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


CROSSREF_API_URL = "https://api.crossref.org/works"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_FETCH_ATTEMPTS = 5
REQUEST_TIMEOUT_SECONDS = (10, 60)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_text(value: Any) -> str:
    """Convert Crossref text (including JATS/XML abstracts) to plain text."""
    if value is None:
        return ""
    if isinstance(value, list):
        value = " ".join(str(item) for item in value if item is not None)
    without_tags = _HTML_TAG_RE.sub(" ", unescape(str(value)))
    normalized = normalize_whitespace(without_tags)
    return re.sub(r"\s+([,.;:!?])", r"\1", normalized)


def _unique_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        cleaned = _clean_text(item)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            result.append(cleaned)
            seen.add(key)
    return result


def _format_date_parts(value: Any) -> str:
    if not isinstance(value, dict):
        return ""

    date_parts = value.get("date-parts")
    if isinstance(date_parts, list) and date_parts and isinstance(date_parts[0], list):
        parts = date_parts[0]
        try:
            year = int(parts[0])
            month = int(parts[1]) if len(parts) > 1 else 1
            day = int(parts[2]) if len(parts) > 2 else 1
            return date(year, month, day).isoformat()
        except (IndexError, TypeError, ValueError):
            return ""

    date_time = value.get("date-time")
    if isinstance(date_time, str):
        return date_time[:10]
    return ""


def _first_date(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        parsed = _format_date_parts(item.get(key))
        if parsed:
            return parsed
    return ""


def _author_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    names: list[str] = []
    seen: set[str] = set()
    for author in value:
        if not isinstance(author, dict):
            continue
        name = _clean_text(author.get("name"))
        if not name:
            name_parts = [str(part) for part in (author.get("given"), author.get("family")) if part]
            name = _clean_text(" ".join(name_parts))
        key = name.casefold()
        if name and key not in seen:
            names.append(name)
            seen.add(key)
    return names


def _pdf_url(item: dict[str, Any]) -> str:
    links = item.get("link")
    if not isinstance(links, list):
        return ""

    fallback = ""
    for link in links:
        if not isinstance(link, dict):
            continue
        url = _clean_text(link.get("URL"))
        content_type = str(link.get("content-type", "")).lower()
        if not url:
            continue
        if content_type == "application/pdf":
            return url
        if not fallback and (url.lower().endswith(".pdf") or "/pdf" in url.lower()):
            fallback = url
    return fallback


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref response into stable, serializable paper records."""
    if not isinstance(payload, dict):
        raise ValueError("Crossref payload must be a JSON object.")

    message = payload.get("message")
    items = message.get("items") if isinstance(message, dict) else None
    if not isinstance(items, list):
        raise ValueError("Crossref payload is missing message.items.")

    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue

        doi = _clean_text(item.get("DOI")).lower()
        title = _clean_text(item.get("title"))
        if not doi or not title or doi in seen_ids:
            continue

        categories = _unique_text_list(item.get("subject"))
        if not categories:
            # Crossref often omits topical subjects. Its registered work type is
            # a stable source category and keeps the downstream category field usable.
            work_type = _clean_text(item.get("type"))
            if work_type:
                categories = [work_type]
        published = _first_date(
            item,
            ("published", "published-online", "published-print", "issued", "created"),
        )
        updated = _first_date(item, ("indexed", "deposited", "created"))
        abs_url = _clean_text(item.get("URL")) or f"https://doi.org/{doi}"

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=_clean_text(item.get("abstract")),
                authors=_author_names(item.get("author")),
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=_pdf_url(item),
                comment="",
            )
        )
        seen_ids.add(doi)
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref data with retry and persist both source and parsed artifacts."""
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "VinUni-Day10-Data-Observability-Lab/1.0",
    }

    last_error: Exception | None = None
    for attempt in range(MAX_FETCH_ATTEMPTS):
        try:
            response = requests.get(
                CROSSREF_API_URL,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code in RETRYABLE_STATUS_CODES:
                if attempt == MAX_FETCH_ATTEMPTS - 1:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After", "")
                delay = float(retry_after) if retry_after.isdigit() else 2**attempt
                time.sleep(delay)
                continue

            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Crossref returned a non-object JSON payload.")

            write_json(settings.paths.raw_api_response, payload)
            records = parse_crossref_payload(payload)
            if not records:
                raise ValueError("Crossref returned no usable paper records.")
            write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
            write_json(
                settings.paths.raw_api_response.parent / "source_manifest.json",
                {
                    "source": settings.source_api,
                    "endpoint": CROSSREF_API_URL,
                    "request_url": response.url,
                    "query": settings.source_query,
                    "filter": settings.source_filter,
                    "requested_rows": settings.max_results,
                    "received_items": len(payload.get("message", {}).get("items", [])),
                    "parsed_records": len(records),
                    "fetched_at_utc": datetime.now(UTC).isoformat(),
                },
            )
            return records
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < MAX_FETCH_ATTEMPTS - 1:
                time.sleep(2**attempt)

    raise RuntimeError(f"Unable to fetch usable Crossref records after {MAX_FETCH_ATTEMPTS} attempts.") from last_error


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a persisted raw-record snapshot and validate its record shape."""
    payload = read_json(path)
    if isinstance(payload, dict):
        payload = payload.get("records")
    if not isinstance(payload, list):
        raise ValueError(f"Raw record snapshot must contain a list: {path}")

    field_names = {field.name for field in fields(PaperRecord)}
    records: list[PaperRecord] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Raw record at index {index} is not an object.")
        values = {name: item.get(name) for name in field_names}
        values["authors"] = values["authors"] if isinstance(values["authors"], list) else []
        values["categories"] = values["categories"] if isinstance(values["categories"], list) else []
        for name in field_names - {"authors", "categories"}:
            values[name] = "" if values[name] is None else str(values[name])
        records.append(PaperRecord(**values))
    return records
