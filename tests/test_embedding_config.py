from __future__ import annotations

from core.config import load_settings, require_embedding_credentials


def test_jina_is_default_embedding_provider_with_provider_specific_model(monkeypatch, tmp_path):
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
    monkeypatch.delenv("EMBEDDING_MODEL", raising=False)
    monkeypatch.setenv("JINA_API_KEY", "test-key")

    settings = load_settings(project_dir=tmp_path / "repo")

    assert settings.embedding_provider == "jina"
    assert settings.embedding_model == "jina-embeddings-v5-text-small"
    require_embedding_credentials(settings)


def test_jina_requires_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "jina")
    monkeypatch.setenv("EMBEDDING_MODEL", "jina-embeddings-v5-text-small")
    monkeypatch.delenv("JINA_API_KEY", raising=False)
    settings = load_settings(project_dir=tmp_path / "repo")

    try:
        require_embedding_credentials(settings)
    except RuntimeError as exc:
        assert "JINA_API_KEY" in str(exc)
    else:
        raise AssertionError("Missing JINA_API_KEY should fail fast")
