from __future__ import annotations

from copy import deepcopy
from typing import Any

import pandas as pd


_FIELD_REPAIRS = {
    "blank_summary": ["summary", "summary_chars", "text_for_embedding"],
    "inject_noise": ["text_for_embedding"],
    "truncate_title": ["title", "text_for_embedding"],
    "age_published_dates": ["published", "age_days"],
}


def repair_corrupted_dataframe(
    corrupted: pd.DataFrame,
    good: pd.DataFrame,
    corruption_log: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Repair only logged corruptions by copying trusted values from *good*.

    Unaffected records and fields are kept from ``corrupted``. Missing rows are
    restored, duplicates are removed, and damaged fields are replaced according
    to the explicit paper IDs recorded in the corruption log.
    """
    if "paper_id" not in corrupted or "paper_id" not in good:
        raise ValueError("Both corrupted and good data must contain paper_id.")

    repaired = corrupted.copy(deep=True)
    repaired["paper_id"] = repaired["paper_id"].astype(str)
    trusted = good.drop_duplicates("paper_id", keep="first").copy(deep=True)
    trusted["paper_id"] = trusted["paper_id"].astype(str)
    trusted_by_id = trusted.set_index("paper_id", drop=False)
    entries = {item["corruption"]: item for item in corruption_log.get("entries", [])}
    repair_entries: list[dict[str, Any]] = []
    targeted_ids: set[str] = set()

    duplicate_entry = entries.get("duplicate_rows", {})
    duplicate_ids = {str(value) for value in duplicate_entry.get("affected_paper_ids", [])}
    targeted_ids.update(duplicate_ids)
    duplicate_mask = repaired["paper_id"].duplicated(keep="first") & repaired["paper_id"].isin(duplicate_ids)
    removed = int(duplicate_mask.sum())
    repaired = repaired.loc[~duplicate_mask].copy()
    repair_entries.append(
        {
            "corruption": "duplicate_rows",
            "action": "remove_logged_duplicates",
            "targeted_paper_ids": sorted(duplicate_ids),
            "rows_removed": removed,
            "fields_restored": [],
        }
    )

    missing_entry = entries.get("drop_latest_records", {})
    missing_ids = [str(value) for value in missing_entry.get("affected_paper_ids", [])]
    targeted_ids.update(missing_ids)
    present_ids = set(repaired["paper_id"])
    restore_ids = [paper_id for paper_id in missing_ids if paper_id not in present_ids and paper_id in trusted_by_id.index]
    if restore_ids:
        restored_rows = trusted_by_id.loc[restore_ids, trusted.columns]
        if isinstance(restored_rows, pd.Series):
            restored_rows = restored_rows.to_frame().T
        repaired = pd.concat([repaired, restored_rows], ignore_index=True)
    repair_entries.append(
        {
            "corruption": "drop_latest_records",
            "action": "restore_missing_rows",
            "targeted_paper_ids": missing_ids,
            "rows_added": len(restore_ids),
            "fields_restored": list(trusted.columns),
        }
    )

    for corruption, fields in _FIELD_REPAIRS.items():
        entry = entries.get(corruption, {})
        paper_ids = [str(value) for value in entry.get("affected_paper_ids", [])]
        targeted_ids.update(paper_ids)
        restored_ids: list[str] = []
        for paper_id in paper_ids:
            matches = repaired.index[repaired["paper_id"].eq(paper_id)]
            if paper_id not in trusted_by_id.index or len(matches) == 0:
                continue
            for field in fields:
                if field in repaired.columns and field in trusted.columns:
                    repaired.at[matches[0], field] = deepcopy(trusted_by_id.at[paper_id, field])
            restored_ids.append(paper_id)
        repair_entries.append(
            {
                "corruption": corruption,
                "action": "restore_logged_fields",
                "targeted_paper_ids": paper_ids,
                "records_repaired": len(restored_ids),
                "fields_restored": fields,
            }
        )

    column_order = [column for column in good.columns if column in repaired.columns]
    repaired = repaired[column_order]
    if {"published", "paper_id"}.issubset(repaired.columns):
        repaired = repaired.sort_values(
            ["published", "paper_id"], ascending=[False, True], kind="stable"
        )
    repaired = repaired.reset_index(drop=True)

    good_ids = set(trusted["paper_id"])
    report = {
        "strategy": "targeted_repair_from_good_data",
        "before": {
            "rows": len(corrupted),
            "unique_paper_ids": int(corrupted["paper_id"].astype(str).nunique()),
        },
        "after": {
            "rows": len(repaired),
            "unique_paper_ids": int(repaired["paper_id"].nunique()),
        },
        "targeted_unique_records": len(targeted_ids),
        "unaffected_reference_records": len(good_ids - targeted_ids),
        "entries": repair_entries,
    }
    return repaired, report
