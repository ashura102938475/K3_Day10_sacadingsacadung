from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings

from core.config import Settings, require_embedding_credentials


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer  # noqa: PLC0415
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required for local embeddings. "
                    "Install it with: uv sync --extra local"
                ) from None

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()


def create_embeddings(settings: Settings) -> Embeddings:
    """Return the correct embeddings backend based on settings.

    - If ``EMBEDDING_PROVIDER`` is ``jina``, uses the Jina AI REST API.
    - Otherwise falls back to the local SentenceTransformer model.
    """
    provider = settings.embedding_provider.strip().lower()
    require_embedding_credentials(settings)

    if provider == "jina":
        from retrieval.jina_embeddings import JinaEmbeddings  # noqa: PLC0415

        return JinaEmbeddings(
            api_key=settings.jina_api_key or "",
            model_name=settings.embedding_model,
        )

    return MiniLMEmbeddings(model_name=settings.embedding_model)
