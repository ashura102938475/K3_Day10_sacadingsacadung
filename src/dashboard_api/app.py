from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.config import Settings, load_settings
from core.utils import first_sentence
from retrieval.index import LocalEmbeddingIndex, SearchResult
from retrieval.llm import build_llm


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=12)
    top_k: int = Field(default=4, ge=1, le=8)


class SourceItem(BaseModel):
    paper_id: str
    title: str
    score: float
    url: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    mode: Literal["rag_llm", "retrieval_fallback"]
    model: str


@dataclass(frozen=True)
class Runtime:
    settings: Settings
    index: LocalEmbeddingIndex


@lru_cache(maxsize=1)
def get_runtime() -> Runtime:
    settings = load_settings()
    if not settings.paths.embeddings_json.exists():
        raise RuntimeError(
            f"Missing embedding manifest: {settings.paths.embeddings_json}. Run pipelines.phase1 first."
        )
    return Runtime(
        settings=settings,
        index=LocalEmbeddingIndex.load(settings, settings.paths.embeddings_json),
    )


def _history_text(history: list[HistoryMessage]) -> str:
    recent = history[-6:]
    if not recent:
        return "No previous conversation."
    return "\n".join(f"{item.role.title()}: {item.content}" for item in recent)


def _context_text(results: list[SearchResult]) -> str:
    return "\n\n".join(
        f"[Source {position}]\npaper_id: {item.paper_id}\ntitle: {item.title}\n{item.content}"
        for position, item in enumerate(results, start=1)
    )


def _message_content(response) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts = [
            str(block.get("text", ""))
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        return "\n".join(part for part in text_parts if part).strip()
    return str(content).strip()


def _fallback_answer(results: list[SearchResult]) -> str:
    if not results:
        return "I could not find supporting evidence in the indexed paper corpus."
    top = results[0]
    summary = str(top.metadata.get("summary", "")).strip()
    evidence = first_sentence(summary) if summary else top.content
    return (
        "The language model is currently unavailable, so this is a retrieval-only response. "
        f"The closest indexed paper is “{top.title}”. {evidence}"
    )


def answer_chat(request: ChatRequest) -> ChatResponse:
    runtime = get_runtime()
    results = runtime.index.search(request.message.strip(), top_k=request.top_k)
    sources = [
        SourceItem(
            paper_id=item.paper_id,
            title=item.title,
            score=round(item.score, 4),
            url=str(item.metadata.get("abs_url", "")),
        )
        for item in results
    ]

    prompt = f"""
Conversation so far:
{_history_text(request.history)}

User question:
{request.message.strip()}

Retrieved evidence:
{_context_text(results) or "No evidence was retrieved."}

Answer the user's question using only the retrieved evidence. Cite supporting items inline as
[Source 1], [Source 2], and so on. If the evidence is insufficient, say that clearly. Keep the
answer concise and do not invent facts.
""".strip()

    try:
        llm = build_llm(runtime.settings, temperature=0.0)
        response = llm.invoke(
            [
                (
                    "system",
                    "You are QualiTrace Assistant, a grounded research-paper RAG assistant.",
                ),
                ("human", prompt),
            ]
        )
        answer = _message_content(response)
        if not answer:
            raise RuntimeError("The language model returned an empty answer.")
        mode: Literal["rag_llm", "retrieval_fallback"] = "rag_llm"
    except Exception:
        answer = _fallback_answer(results)
        mode = "retrieval_fallback"

    return ChatResponse(
        answer=answer,
        sources=sources,
        mode=mode,
        model=runtime.settings.model_name,
    )


app = FastAPI(title="QualiTrace RAG API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
def health() -> dict[str, object]:
    settings = load_settings()
    return {
        "status": "ok",
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.model_name,
        "index_ready": settings.paths.embeddings_json.exists(),
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        return answer_chat(request)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"RAG runtime unavailable: {exc}") from exc
