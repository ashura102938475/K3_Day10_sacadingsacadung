from __future__ import annotations

from dataclasses import replace

from dashboard_api import app as dashboard
from retrieval.index import SearchResult


class _FakeIndex:
    def search(self, query: str, top_k: int):
        assert query == "What is SafeRAG?"
        assert top_k == 4
        return [
            SearchResult(
                paper_id="10.1234/saferag",
                title="SafeRAG",
                score=0.91,
                content="Title: SafeRAG | Authors: A. Author | Summary: SafeRAG improves grounded reports.",
                metadata={
                    "summary": "SafeRAG improves grounded reports. It uses hierarchical retrieval.",
                    "abs_url": "https://doi.org/10.1234/saferag",
                },
            )
        ]


def test_chat_returns_grounded_retrieval_fallback(monkeypatch):
    settings = dashboard.load_settings()
    runtime = dashboard.Runtime(
        settings=replace(settings, model_name="test-model"),
        index=_FakeIndex(),
    )
    monkeypatch.setattr(dashboard, "get_runtime", lambda: runtime)
    monkeypatch.setattr(
        dashboard,
        "build_llm",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    response = dashboard.answer_chat(
        dashboard.ChatRequest(message="What is SafeRAG?")
    )

    assert response.mode == "retrieval_fallback"
    assert "SafeRAG" in response.answer
    assert response.sources[0].paper_id == "10.1234/saferag"
    assert response.sources[0].score == 0.91
