from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import random
from typing import Any

import pandas as pd

from core.utils import write_json


_SEED = 42
_NOISE_TOKENS = ["XXXX", "###", "???", "!!!", "ERR", "N/A", "null", "undefined"]


def _random_state() -> random.Random:
    return random.Random(_SEED)


def _rebuild_embedding_text(row: pd.Series) -> str:
    title = str(row.get("title", ""))
    authors = str(row.get("authors_joined", ""))
    summary = str(row.get("summary", ""))
    return f"Title: {title} | Authors: {authors} | Summary: {summary}"


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: str | Path) -> pd.DataFrame:
    """Simulate multiple realistic data corruption scenarios on a clean DataFrame.

    Corruption types applied (in order):
    1. Drop 2 latest records (freshness loss).
    2. Blank summary on 2 rows (completeness).
    3. Inject noise tokens into 2 text_for_embedding fields (accuracy).
    4. Truncate 2 titles (completeness).
    5. Age 2 published dates by +365 days (freshness/validity).
    6. Duplicate 2 rows (uniqueness).

    After all corruptions are applied, ``text_for_embedding`` is rebuilt for every
    affected row and a structured corruption log is written to *output_log_path*.
    """
    rng = _random_state()
    output_log_path = Path(output_log_path)
    corrupted = df.copy()
    total = len(corrupted)
    log_entries: list[dict[str, Any]] = []

    # --- 1. Drop latest records ---
    drop_count = min(2, total)
    if "published" in corrupted.columns:
        sorted_df = corrupted.sort_values("published", ascending=False, kind="stable")
        drop_indices = sorted_df.index[:drop_count].tolist()
    else:
        drop_indices = corrupted.index[:drop_count].tolist()
    dropped_paper_ids = [str(corrupted.at[idx, "paper_id"]) for idx in drop_indices]
    corrupted = corrupted.drop(index=drop_indices)
    log_entries.append(
        {
            "corruption": "drop_latest_records",
            "count": drop_count,
            "affected_paper_ids": dropped_paper_ids,
            "description": f"Dropped {drop_count} latest records to simulate freshness loss.",
        }
    )

    # --- 2. Blank summary ---
    blank_count = min(2, len(corrupted))
    blank_indices = rng.sample(list(corrupted.index), blank_count)
    blank_paper_ids: list[str] = []
    for idx in blank_indices:
        blank_paper_ids.append(str(corrupted.at[idx, "paper_id"]))
        corrupted.at[idx, "summary"] = ""
        corrupted.at[idx, "summary_chars"] = 0
    log_entries.append(
        {
            "corruption": "blank_summary",
            "count": blank_count,
            "affected_paper_ids": blank_paper_ids,
            "description": f"Set summary to empty string on {blank_count} rows.",
        }
    )

    # --- 3. Inject noise into text_for_embedding ---
    noise_count = min(2, len(corrupted))
    available = [i for i in corrupted.index if i not in set(blank_indices)]
    if len(available) < noise_count:
        available = list(corrupted.index)
    noise_indices = rng.sample(available, noise_count)
    noise_paper_ids: list[str] = []
    for idx in noise_indices:
        noise_paper_ids.append(str(corrupted.at[idx, "paper_id"]))
    log_entries.append(
        {
            "corruption": "inject_noise",
            "count": noise_count,
            "affected_paper_ids": noise_paper_ids,
            "description": f"Injected noise tokens into text_for_embedding on {noise_count} rows.",
        }
    )

    # --- 4. Truncate titles ---
    trunc_count = min(2, len(corrupted))
    used = set(blank_indices) | set(noise_indices)
    trunc_available = [i for i in corrupted.index if i not in used]
    if len(trunc_available) < trunc_count:
        trunc_available = list(corrupted.index)
    trunc_indices = rng.sample(trunc_available, trunc_count)
    trunc_paper_ids: list[str] = []
    for idx in trunc_indices:
        trunc_paper_ids.append(str(corrupted.at[idx, "paper_id"]))
        title = str(corrupted.at[idx, "title"])
        cut = max(5, len(title) // 3)
        corrupted.at[idx, "title"] = title[:cut].rstrip() + "…"
    log_entries.append(
        {
            "corruption": "truncate_title",
            "count": trunc_count,
            "affected_paper_ids": trunc_paper_ids,
            "description": f"Truncated titles to ~1/3 length on {trunc_count} rows.",
        }
    )

    # --- 5. Age published dates ---
    age_count = min(2, len(corrupted))
    used = set(blank_indices) | set(noise_indices) | set(trunc_indices)
    age_available = [i for i in corrupted.index if i not in used]
    if len(age_available) < age_count:
        age_available = [i for i in corrupted.index if i not in set(blank_indices)]
    age_indices = rng.sample(age_available, age_count)
    age_paper_ids: list[str] = []
    for idx in age_indices:
        age_paper_ids.append(str(corrupted.at[idx, "paper_id"]))
        raw = str(corrupted.at[idx, "published"])
        try:
            dt = pd.Timestamp(raw)
            aged = dt - timedelta(days=365)
            corrupted.at[idx, "published"] = aged.strftime("%Y-%m-%d")
            if corrupted.at[idx, "age_days"] is not None and not pd.isna(corrupted.at[idx, "age_days"]):
                corrupted.at[idx, "age_days"] = int(corrupted.at[idx, "age_days"]) + 365
        except Exception:
            pass
    log_entries.append(
        {
            "corruption": "age_published_dates",
            "count": age_count,
            "affected_paper_ids": age_paper_ids,
            "description": f"Aged published dates by -365 days on {age_count} rows.",
        }
    )

    # Rebuild derived embedding text by stable paper_id before adding
    # intentional embedding-only noise and duplicates. DataFrame indexes are
    # not stable after dropping/concatenating rows.
    rebuild_paper_ids = set(blank_paper_ids) | set(trunc_paper_ids)
    rebuild_mask = corrupted["paper_id"].astype(str).isin(rebuild_paper_ids)
    for idx in corrupted.index[rebuild_mask]:
        corrupted.at[idx, "text_for_embedding"] = _rebuild_embedding_text(corrupted.loc[idx])

    # Re-apply intentional noise after derived fields are synchronized.
    for paper_id in noise_paper_ids:
        matching = corrupted.index[corrupted["paper_id"].astype(str).eq(paper_id)]
        for idx in matching:
            original = str(corrupted.at[idx, "text_for_embedding"])
            tokens = original.split()
            if len(tokens) >= 5:
                for _ in range(max(1, len(tokens) // 5)):
                    pos = rng.randint(0, len(tokens) - 1)
                    tokens[pos] = rng.choice(_NOISE_TOKENS)
            corrupted.at[idx, "text_for_embedding"] = " ".join(tokens)

    # --- 6. Duplicate rows ---
    dup_count = min(2, len(corrupted))
    dup_indices = rng.sample(list(corrupted.index), dup_count)
    dup_paper_ids: list[str] = []
    dup_rows = corrupted.loc[dup_indices].copy()
    for _, row in dup_rows.iterrows():
        dup_paper_ids.append(str(row["paper_id"]))
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    log_entries.append(
        {
            "corruption": "duplicate_rows",
            "count": dup_count,
            "affected_paper_ids": dup_paper_ids,
            "description": f"Duplicated {dup_count} rows to break uniqueness.",
        }
    )

    # Ensure column order matches the clean contract.
    clean_cols = [c for c in df.columns if c in corrupted.columns]
    corrupted = corrupted[clean_cols].reset_index(drop=True)

    # --- 8. Write corruption log ---
    log_payload = {
        "original_rows": total,
        "corrupted_rows": len(corrupted),
        "corruptions_applied": [e["corruption"] for e in log_entries],
        "entries": log_entries,
    }
    write_json(output_log_path, log_payload)

    return corrupted
