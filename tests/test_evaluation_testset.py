from __future__ import annotations

from collections import Counter

import pandas as pd

from core.utils import read_json
from evaluation.testset import build_test_set


def test_build_test_set_creates_ten_diverse_questions(tmp_path):
    dataframe = pd.DataFrame(
        [
            {
                "paper_id": f"10.1234/paper-{index:02d}",
                "title": f"Paper {index:02d}",
                "summary": f"Summary sentence {index}. Additional supporting detail for evaluation.",
                "authors_joined": f"Author {index}",
                "categories_joined": "journal-article" if index % 2 else "posted-content",
                "published": f"2026-{index:02d}-01",
            }
            for index in range(1, 13)
        ]
    )
    output_path = tmp_path / "test_set.json"

    test_set = build_test_set(dataframe, output_path)

    assert len(test_set) == 10
    assert len({item["id"] for item in test_set}) == 10
    assert len({item["ground_truth_doc_ids"][0] for item in test_set}) == 10
    assert Counter(item["question_type"] for item in test_set) == {
        "summary": 3,
        "authors": 3,
        "date": 2,
        "categories": 2,
    }
    assert read_json(output_path) == test_set
