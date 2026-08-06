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
    data_state: Literal["baseline", "corrupted", "repaired"] = "baseline"


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
    data_state: Literal["baseline", "corrupted", "repaired"]


@dataclass(frozen=True)
class Runtime:
    settings: Settings
    index: LocalEmbeddingIndex


@lru_cache(maxsize=3)
def get_runtime(data_state: str = "baseline") -> Runtime:
    settings = load_settings()
    manifest_paths = {
        "baseline": settings.paths.embeddings_json,
        "corrupted": settings.paths.corrupted_embeddings_json,
        "repaired": settings.paths.repaired_embeddings_json,
    }
    manifest_path = manifest_paths.get(data_state)
    if manifest_path is None:
        raise RuntimeError(f"Trạng thái dữ liệu không được hỗ trợ: {data_state}")
    if not manifest_path.exists():
        raise RuntimeError(
            f"Thiếu embedding manifest: {manifest_path}. Hãy chạy pipeline tương ứng trước."
        )
    return Runtime(
        settings=settings,
        index=LocalEmbeddingIndex.load(settings, manifest_path),
    )


def _history_text(history: list[HistoryMessage]) -> str:
    recent = history[-6:]
    if not recent:
        return "Chưa có hội thoại trước đó."
    role_names = {"user": "Người dùng", "assistant": "Trợ lý"}
    return "\n".join(f"{role_names[item.role]}: {item.content}" for item in recent)


def _context_text(results: list[SearchResult]) -> str:
    return "\n\n".join(
        f"[Nguồn {position}]\nmã bài báo: {item.paper_id}\ntiêu đề: {item.title}\n{item.content}"
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
        return "Tôi chưa tìm thấy bằng chứng phù hợp trong kho bài báo đã lập chỉ mục."
    top = results[0]
    summary = str(top.metadata.get("summary", "")).strip()
    evidence = first_sentence(summary) if summary else top.content
    return (
        "Mô hình ngôn ngữ hiện không khả dụng nên đây là câu trả lời chỉ dựa trên kết quả truy xuất. "
        f"Bài báo gần nhất là “{top.title}”. {evidence}"
    )


def answer_chat(request: ChatRequest) -> ChatResponse:
    runtime = get_runtime(request.data_state)
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
Lịch sử hội thoại:
{_history_text(request.history)}

Câu hỏi của người dùng:
{request.message.strip()}

Trạng thái dữ liệu đang truy vấn: {request.data_state}

Bằng chứng đã truy xuất:
{_context_text(results) or "Không truy xuất được bằng chứng."}

Hãy trả lời bằng tiếng Việt, chỉ sử dụng bằng chứng đã truy xuất. Trích dẫn nguồn ngay trong câu
trả lời dưới dạng [Nguồn 1], [Nguồn 2]... Nếu bằng chứng chưa đủ, hãy nói rõ. Trả lời ngắn gọn,
có cấu trúc Markdown dễ đọc và tuyệt đối không bịa thông tin. Chỉ đổi ngôn ngữ nếu người dùng
yêu cầu rõ ràng.
""".strip()

    try:
        llm = build_llm(runtime.settings, temperature=0.0)
        response = llm.invoke(
            [
                (
                    "system",
                    "Bạn là QualiTrace Assistant, trợ lý RAG về bài báo khoa học, ưu tiên tiếng Việt và luôn bám sát nguồn.",
                ),
                ("human", prompt),
            ]
        )
        answer = _message_content(response)
        if not answer:
            raise RuntimeError("Mô hình ngôn ngữ trả về câu trả lời rỗng.")
        mode: Literal["rag_llm", "retrieval_fallback"] = "rag_llm"
    except Exception:
        answer = _fallback_answer(results)
        mode = "retrieval_fallback"

    return ChatResponse(
        answer=answer,
        sources=sources,
        mode=mode,
        model=runtime.settings.model_name,
        data_state=request.data_state,
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
        "available_data_states": {
            "baseline": settings.paths.embeddings_json.exists(),
            "corrupted": settings.paths.corrupted_embeddings_json.exists(),
            "repaired": settings.paths.repaired_embeddings_json.exists(),
        },
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        return answer_chat(request)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"RAG runtime không khả dụng: {exc}") from exc
