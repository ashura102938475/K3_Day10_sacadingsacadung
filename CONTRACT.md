# CONTRACT.md — Data Contract & Role Assignment

> **Mục đích:** Hợp đồng kỹ thuật chung cho toàn nhóm. Mọi thành viên phải tuân thủ các schema,
> đường dẫn, và quy ước trong file này khi code song song. Cập nhật file này nếu có thay đổi.
>
> **Trạng thái hiện tại:** Nhiều module đã được implement. File này phản ánh code thực tế
> (không phải starter template).

---

## 1. Phân công (2 thành viên)

| # | Thành viên | MSSV | Vai trò | Đã implement | Hỗ trợ / refactor |
|:--|-----------|------|---------|-------------|-------------------|
| 1 | **Nguyễn Anh Trà** | 2A202601735 | Corruption, Observability, Pipeline, Multi-Provider Owner | `corruption.py`, `quality.py`, `reporting.py`, `phase1.py`, `corruption_flow.py`, `jina_embeddings.py` | `embeddings.py` (Jina factory), `config.py` (Jina + NVIDIA + embedding), `llm.py` (NVIDIA), `index.py`, `metrics.py`, `.env.example`, `pyproject.toml` |
| 2 | **Nguyễn Chí Hiếu** | 2A202601931 | Ingestion, Retrieval, Eval, UI Owner | `crossref.py`, `cleaning.py`, `testset.py`, `embeddings.py`, `index.py`, `llm.py`, `agent.py`, `qa.py`, `utils.py`, Stitch UI dashboard | Refactor + harden: `corruption.py`, `quality.py`, `corruption_flow.py`, `phase1.py`, `jina_embeddings.py`, `index.py`, `embeddings.py`, `config.py`, `metrics.py` |

> **Ghi chú:** Hiếu đã hoàn thành baseline (ingestion → cleaning → embedding → index → eval set) trước.
> Trà đã implement toàn bộ các module TODO còn lại (corruption, observability, pipelines), đồng thời bổ sung Jina embeddings và NVIDIA LLM provider.
> Hiếu sau đó refactor, harden code của Trà, thêm tests, data artifacts, và Stitch UI dashboard.

---

## 2. Luồng dữ liệu (thực tế)

```
Crossref API
  │
  ▼
crossref.py ──► data/raw/crossref_response.json
  │             data/raw/crossref_records.json
  │             data/raw/source_manifest.json
  ▼
cleaning.py ──► data/clean/papers_clean.csv       (16 columns)
  │             data/clean/papers_clean.json
  │             data/clean/cleaning_summary.json
  ├──► testset.py      ──► data/eval/test_set.json        (10 questions, 4 types)
  ├──► embeddings.py   ──► sentence-transformers          (MiniLMEmbeddings)
  ├──► index.py        ──► data/chroma/                   (ChromaDB PersistentClient)
  │                        data/embeddings/papers_embeddings.json
  ├──► qa.py           ──► AnswerResult                   (rule-based extraction)
  ├──► agent.py        ──► LangChain agent                (search + lookup tools)
  │
  ▼ (CHƯA IMPLEMENT)
corruption.py ──► data/clean/papers_clean_corrupted.csv
                   data/results/corruption_log.json
  │
  ▼ (CHƯA IMPLEMENT)
corruption_flow.py ──► data/results/corrupted_metrics.json
                       data/results/repaired_metrics.json
                       data/reports/corruption_report.md
```

---

## 3. Schema hợp đồng (khớp code thực tế)

### 3.1 Raw Schema — `PaperRecord` (đã implement)

```python
# src/ingestion/crossref.py — @dataclass(frozen=True)
class PaperRecord:
    paper_id: str          # DOI (lowercased), unique non-null
    title: str             # Đã clean HTML tags, normalize whitespace
    summary: str           # Abstract đã clean (JATS/XML → plain text)
    authors: list[str]     # ["GivenName FamilyName", ...], deduplicated
    categories: list[str]  # Subject categories, fallback → work type
    primary_category: str  # categories[0] hoặc ""
    published: str         # ISO date "YYYY-MM-DD" (ưu tiên: published > published-online > published-print > issued > created)
    updated: str           # ISO date (ưu tiên: indexed > deposited > created)
    abs_url: str           # URL từ item hoặc f"https://doi.org/{doi}"
    pdf_url: str           # Link PDF nếu có, ngược lại ""
    comment: str           # Luôn "" (không parse)
```

### 3.2 Clean Schema — DataFrame columns (đã implement)

**File:** `data/clean/papers_clean.csv` | **Số dòng:** 24 | **Số cột:** 16

| # | Column | Kiểu | Non-null | Mô tả |
|:--|--------|------|:--------:|-------|
| 1 | `paper_id` | `str` | ✅ | DOI (lowercased), unique |
| 2 | `title` | `str` | ✅ | Đã normalize whitespace, strip HTML |
| 3 | `summary` | `str` | ✅ | Abstract ≥ 100 chars |
| 4 | `authors` | `list[str]` | | List tác giả (stored as Python list in JSON, stringified in CSV) |
| 5 | `categories` | `list[str]` | | List chủ đề |
| 6 | `primary_category` | `str` | | Chủ đề đầu tiên |
| 7 | `published` | `str` | ✅ | ISO date `YYYY-MM-DD` |
| 8 | `updated` | `str` | | ISO date hoặc `""` |
| 9 | `abs_url` | `str` | | Link DOI |
| 10 | `pdf_url` | `str` | | Link PDF hoặc `""` |
| 11 | `comment` | `str` | | Luôn `""` |
| 12 | `authors_joined` | `str` | | `", "`.join(authors) |
| 13 | `categories_joined` | `str` | | `", "`.join(categories) |
| 14 | `summary_chars` | `int` | | `len(summary)` |
| 15 | `age_days` | `int` | ✅ | `(run_date - published_date).days` |
| 16 | `text_for_embedding` | `str` | ✅ | Format bên dưới |

**`text_for_embedding` format (đã implement):**
```
Title: {title} | Authors: {authors_joined} | Summary: {summary}
```
> ⚠️ Không bao gồm categories.

**Document ID trong ChromaDB:** `"{paper_id}::{index}"` (DOI + row index)

### 3.3 Cleaning rules (đã implement)

| # | Quy tắc | Dimension | Hành động |
|:--|---------|-----------|-----------|
| 1 | `paper_id` rỗng | Completeness | **Drop record** |
| 2 | `title` rỗng | Completeness | **Drop record** |
| 3 | `len(summary) < 100` | Completeness | **Drop record** |
| 4 | `published` date không parse được | Validity | **Drop record** |
| 5 | `paper_id` duplicate | Uniqueness | **Giữ bản đầu, drop bản sau** |
| 6 | Title/summary có HTML tags | Consistency | Strip tags + unescape |
| 7 | Whitespace thừa | Consistency | `normalize_whitespace()` |
| 8 | Authors/categories trùng lặp | Consistency | Deduplicate case-insensitive |

> **Quan trọng:** `age_days` luôn có giá trị hợp lệ vì row có `published` không parse được đã bị drop.
> Không có fallback `-1`.

### 3.4 Evaluation Set Schema (đã implement)

**File:** `data/eval/test_set.json` | **Số câu hỏi:** 10 | **Số loại:** 4

```json
{
  "id": "summary-01",
  "question_type": "summary",
  "question": "What is the paper '{title}' about?",
  "ground_truth": "<câu đầu tiên của summary>",
  "ground_truth_doc_ids": ["10.xxxx/paper1"]
}
```

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `id` | `str` | `"{question_type}-{counter:02d}"` |
| `question_type` | `str` | `summary` \| `authors` \| `date` \| `categories` |
| `question` | `str` | Câu hỏi có nhúng `'{title}'` trong single quote |
| `ground_truth` | `str` | Với summary: `first_sentence(summary)`, còn lại: giá trị trường tương ứng |
| `ground_truth_doc_ids` | `list[str]` | 1 phần tử — `paper_id` của document nguồn |

**Phân bố câu hỏi:** `summary`×3, `authors`×3, `date`×2, `categories`×2 (xen kẽ, deterministic)

---

## 4. Artifact paths — quy ước chung

| Artifact | Đường dẫn | Trạng thái |
|----------|-----------|:----------:|
| Raw API response | `data/raw/crossref_response.json` | ✅ |
| Raw records | `data/raw/crossref_records.json` | ✅ |
| Source manifest | `data/raw/source_manifest.json` | ✅ |
| Clean CSV | `data/clean/papers_clean.csv` | ✅ |
| Clean JSON | `data/clean/papers_clean.json` | ✅ |
| Cleaning summary | `data/clean/cleaning_summary.json` | ✅ |
| ChromaDB | `data/chroma/` | ✅ |
| Embeddings manifest | `data/embeddings/papers_embeddings.json` | ✅ |
| Evaluation set | `data/eval/test_set.json` | ✅ |
| Retrieval smoke test | `data/results/retrieval_smoke_results.json` | ✅ |
| Corrupted CSV | `data/clean/papers_clean_corrupted.csv` | ❌ |
| Corrupted JSON | `data/clean/papers_clean_corrupted.json` | ❌ |
| Repaired CSV | `data/clean/papers_clean_repaired.csv` | ❌ |
| Repaired JSON | `data/clean/papers_clean_repaired.json` | ❌ |
| Baseline metrics | `data/results/baseline_metrics.json` | ❌ |
| Baseline answers | `data/results/baseline_answers.json` | ❌ |
| Corrupted metrics | `data/results/corrupted_metrics.json` | ❌ |
| Repaired metrics | `data/results/repaired_metrics.json` | ❌ |
| Corruption log | `data/results/corruption_log.json` | ❌ |
| Quality checks | `data/quality/` | ❌ |
| Freshness report | `data/quality/freshness_report.json` | ❌ |
| Baseline report | `data/reports/phase1_report.md` | ❌ |
| Comparison report | `data/reports/corruption_report.md` | ❌ |

---

## 5. Quy ước chung

### 5.1 Các module mới (đã implement, không có trong starter)

| Module | Vai trò |
|--------|--------|
| `src/core/utils.py` | `read_json`, `write_json`, `write_csv`, `write_text`, `normalize_whitespace`, `first_sentence`, `safe_slug`, `compact_join`, `now_utc`, `ensure_parent` |
| `src/retrieval/embeddings.py` | `MiniLMEmbeddings` — wrapper quanh `sentence-transformers` |
| `src/retrieval/index.py` | `LocalEmbeddingIndex` + `SearchResult` — ChromaDB build/load/search/lookup |
| `src/retrieval/agent.py` | `build_agent` + `run_agent_question` — LangChain agent |
| `src/retrieval/qa.py` | `answer_question` + `AnswerResult` — rule-based QA extraction |

### 5.2 Embedding Model
- **Fixed:** `sentence-transformers/all-MiniLM-L6-v2`
- **Normalize:** `normalize_embeddings=True`
- **ChromaDB metric:** `cosine`

### 5.3 LLM Provider
- Hỗ trợ: `gemini`, `openai`, `anthropic`, `openrouter`, `ollama`, `custom`, `nvidia`
- `ollama` là lựa chọn duy nhất không cần API key

### 5.4 Environment
- `.env` — gitignored, mỗi người tự tạo từ `.env.example`
- `.env.example` — tracked
- Không commit API key

---

## 6. Việc còn lại

Tất cả các module đã được implement. Trạng thái hiện tại:

| Module | Owner (implement) | Refactor bởi | Mô tả | Trạng thái |
|--------|:-----:|:-----:|-------|:--------:|
| `corruption.py` | **Trà** | Hiếu | Mô phỏng 6 dạng data corruption (drop, blank, noise, truncate, age, duplicate) | ✅ Hoàn thành |
| `quality.py` | **Trà** | Hiếu | 12 data quality checks + freshness report | ✅ Hoàn thành |
| `reporting.py` | **Trà** | — | Markdown report cho baseline + comparison | ✅ Hoàn thành |
| `phase1.py` | **Trà** | Hiếu | Pipeline baseline end-to-end | ✅ Hoàn thành |
| `corruption_flow.py` | **Trà** | Hiếu | Pipeline corrupt → eval → repair → compare | ✅ Hoàn thành |
| `jina_embeddings.py` | **Trà** | Hiếu | Jina AI REST API embeddings (task-aware routing) | ✅ Hoàn thành |

---

*Cập nhật lần cuối: 2026-08-06 — Sync với toàn bộ commit history (04cd41a..d8ce2a9), phản ánh đúng công sức của cả Trà và Hiếu*
