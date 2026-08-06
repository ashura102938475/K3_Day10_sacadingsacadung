from __future__ import annotations

from importlib import import_module


_EXPORTS = {
    "build_agent": (".agent", "build_agent"),
    "run_agent_question": (".agent", "run_agent_question"),
    "MiniLMEmbeddings": (".embeddings", "MiniLMEmbeddings"),
    "LocalEmbeddingIndex": (".index", "LocalEmbeddingIndex"),
    "SearchResult": (".index", "SearchResult"),
    "build_llm": (".llm", "build_llm"),
    "AnswerResult": (".qa", "AnswerResult"),
    "answer_question": (".qa", "answer_question"),
}
__all__ = list(_EXPORTS)


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = _EXPORTS[name]
    value = getattr(import_module(module_name, __name__), attribute_name)
    globals()[name] = value
    return value
