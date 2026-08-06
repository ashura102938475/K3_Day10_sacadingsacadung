from __future__ import annotations

from typing import Any

import requests
from langchain_core.embeddings import Embeddings


JINA_API_URL = "https://api.jina.ai/v1/embeddings"
REQUEST_TIMEOUT = 60
MAX_BATCH_SIZE = 64


class JinaEmbeddings(Embeddings):
    """Embeddings via the Jina AI REST API with task-aware routing.

    Uses ``retrieval.passage`` for documents and ``retrieval.query`` for
    queries, which improves asymmetric retrieval quality.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "jina-embeddings-v5-text-small",
        base_url: str = JINA_API_URL,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url

    def _embed(self, texts: list[str], task: str) -> list[list[float]]:
        if not texts:
            return []
        if not self.api_key:
            raise RuntimeError("JINA_API_KEY is required to call the Jina embeddings API.")

        embeddings: list[list[float]] = []
        for start in range(0, len(texts), MAX_BATCH_SIZE):
            embeddings.extend(self._embed_batch(texts[start : start + MAX_BATCH_SIZE], task))
        return embeddings

    def _embed_batch(self, texts: list[str], task: str) -> list[list[float]]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload: dict[str, Any] = {
            "model": self.model_name,
            "task": task,
            "normalized": True,
            "input": texts,
        }
        response = requests.post(
            self.base_url,
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload_data = response.json()
        items = sorted(payload_data.get("data", []), key=lambda item: item.get("index", 0))
        vectors = [item["embedding"] for item in items]
        if len(vectors) != len(texts):
            raise RuntimeError(
                f"Jina returned {len(vectors)} embeddings for {len(texts)} inputs."
            )
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, task="retrieval.passage")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], task="retrieval.query")[0]
