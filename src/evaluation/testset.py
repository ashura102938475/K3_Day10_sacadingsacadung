from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


QUESTION_TYPES = (
    "summary",
    "authors",
    "date",
    "categories",
    "summary",
    "authors",
    "date",
    "categories",
    "summary",
    "authors",
)
REQUIRED_COLUMNS = {
    "paper_id",
    "title",
    "summary",
    "authors_joined",
    "categories_joined",
    "published",
}


def _evenly_spaced_rows(dataframe: pd.DataFrame, count: int) -> list[pd.Series]:
    if count == 1:
        return [dataframe.iloc[0]]
    last_index = len(dataframe) - 1
    positions = [round(index * last_index / (count - 1)) for index in range(count)]
    return [dataframe.iloc[position] for position in positions]


def _question_and_answer(question_type: str, row: pd.Series) -> tuple[str, str]:
    title = str(row["title"])
    if question_type == "summary":
        return f"What is the paper '{title}' about?", first_sentence(str(row["summary"]))
    if question_type == "authors":
        return f"Who authored the paper '{title}'?", str(row["authors_joined"])
    if question_type == "date":
        return f"When was the paper '{title}' published?", str(row["published"])
    if question_type == "categories":
        return f"What categories are assigned to the paper '{title}'?", str(row["categories_joined"])
    raise ValueError(f"Unsupported question type: {question_type}")


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a deterministic, diverse 10-question evaluation set."""
    missing_columns = REQUIRED_COLUMNS - set(df.columns)
    if missing_columns:
        raise ValueError(f"Clean dataframe is missing columns: {sorted(missing_columns)}")

    candidates = df.copy()
    for column in REQUIRED_COLUMNS:
        candidates = candidates[candidates[column].notna()]
        candidates = candidates[candidates[column].astype(str).str.strip().ne("")]

    # The starter QA helper uses single-quoted titles for exact lookup.
    candidates = candidates[~candidates["title"].astype(str).str.contains("'", regex=False)]
    candidates = candidates.drop_duplicates(subset=["paper_id"], keep="first")
    candidates = candidates.sort_values(
        by=["published", "paper_id"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)
    if len(candidates) < len(QUESTION_TYPES):
        raise ValueError(
            f"At least {len(QUESTION_TYPES)} complete, unique documents are required; "
            f"found {len(candidates)}."
        )

    selected_rows = _evenly_spaced_rows(candidates, len(QUESTION_TYPES))
    counters = {question_type: 0 for question_type in set(QUESTION_TYPES)}
    test_set: list[dict[str, Any]] = []
    for question_type, row in zip(QUESTION_TYPES, selected_rows, strict=True):
        counters[question_type] += 1
        question, ground_truth = _question_and_answer(question_type, row)
        test_set.append(
            {
                "id": f"{question_type}-{counters[question_type]:02d}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [str(row["paper_id"])],
            }
        )

    write_json(Path(output_path), test_set)
    return test_set
