# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung |
| ----------------- | -------- |
| Khóa/Lớp          | K3 |
| Tên nhóm          | sacadingsacadung |
| Repository         | https://github.com/ashura102938475/K3_Day10_sacadingsacadung |
| Ngày hoàn thành   | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Đã implement | Hỗ trợ / refactor |
| --: | --- | --- | --- | --- | --- |
| 1 | Nguyễn Anh Trà | 2A202601735 | Corruption, Observability, Pipeline, Multi-Provider Owner | `corruption.py`, `quality.py`, `reporting.py`, `phase1.py`, `corruption_flow.py`, `jina_embeddings.py` | `embeddings.py`, `config.py`, `llm.py`, `index.py`, `metrics.py`, `.env.example`, `pyproject.toml` |
| 2 | Nguyễn Chí Hiếu | 2A202601931 | Ingestion, Retrieval, Eval, UI Owner | `crossref.py`, `cleaning.py`, `testset.py`, `embeddings.py`, `index.py`, `llm.py`, `agent.py`, `qa.py`, `utils.py`, Stitch UI | Refactor + harden code của Trà, thêm tests, data artifacts |

> **Ghi chú:** Hiếu đã hoàn thành baseline (ingestion → cleaning → embedding → index → eval set) trước. Trà sau đó implement toàn bộ module TODO còn lại (corruption, observability, pipelines) và bổ sung Jina embeddings + NVIDIA LLM provider. Hiếu refactor, harden code của Trà, thêm tests, data artifacts, và Stitch UI dashboard.

## 2. Tóm tắt kết quả

Viết từ 150–250 từ, trả lời ngắn gọn:

- Nhóm đã hoàn thành những phần nào?
- Baseline pipeline đã tạo ra các artifact nào?
- Corruption nào ảnh hưởng rõ nhất đến data quality hoặc agent?
- Repair đã phục hồi được chỉ số nào?
- Blocker hoặc giới hạn quan trọng nhất còn lại là gì?

**Tóm tắt của nhóm:**

Nhóm đã hoàn thành toàn bộ data pipeline end-to-end qua 3 trạng thái (baseline → corrupted → repaired). Baseline pipeline tạo đầy đủ artifacts: raw records (24 papers từ Crossref), cleaned dataset (24 rows × 16 columns, 0 dropped), ChromaDB index (cosine metric), evaluation set (10 câu hỏi × 4 loại), quality checks (12/12 passed), và freshness report. Corruption flow áp dụng 6 loại corruption có chủ đích: drop latest records, blank summary, noise injection vào text_for_embedding, truncate title, age published dates, và duplicate rows. Các corruption ảnh hưởng đến `text_for_embedding` (blank summary, noise injection) gây tác động rõ nhất đến retrieval metrics vì trực tiếp làm hỏng chất lượng embedding. Repair strategy rebuild toàn bộ từ raw source records → tất cả metrics phục hồi về baseline. Hệ thống hỗ trợ 7 LLM providers và 2 embedding providers (Jina API + local MiniLM).

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

Điều chỉnh sơ đồ dưới đây nếu cách triển khai thực tế của nhóm khác starter:

```text
Crossref API
    -> raw response/raw records
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner | Status |
| ----- | ----- | ----------- | --------------- | ----- |:------:|
| Ingestion | Crossref REST API | Fetch với retry (429/5xx), parse JATS/XML → `PaperRecord`, dedup | `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, `data/raw/source_manifest.json` | Hiếu | ✅ |
| Cleaning | `data/raw/crossref_records.json` | Normalize HTML, validate (summary ≥100 chars, published parseable), drop duplicates, sort by published desc | `data/clean/papers_clean.csv` (16 cols), `data/clean/papers_clean.json`, `data/clean/cleaning_summary.json` | Hiếu | ✅ |
| Embedding/index | `data/clean/papers_clean.csv` | `sentence-transformers/all-MiniLM-L6-v2` + ChromaDB PersistentClient, cosine similarity | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Hiếu | ✅ |
| Evaluation | `data/clean/papers_clean.csv` | 10 câu hỏi deterministic (summary×3, authors×3, date×2, categories×2), `first_sentence()` cho ground truth | `data/eval/test_set.json` | Hiếu | ✅ |
| Retrieval QA | Embedding index | Rule-based answer extraction (who/when/what categories) + semantic search fallback | `AnswerResult` (question, answer, retrieved_doc_ids) | Hiếu | ✅ |
| LangChain Agent | LLM + index | `semantic_search_papers` + `lookup_paper` tools | Agent runner | Hiếu | ✅ |
| Observability | `data/clean/papers_clean.csv` | 12 data quality checks, freshness report | `data/quality/`, `data/quality/freshness_report.json` | Trà | ✅ |
| Corruption | `data/clean/papers_clean.csv` | 6 dạng corruption (drop, blank summary, noise, truncate, age, duplicate) | `data/clean/papers_clean_corrupted.csv`, `data/results/corruption_log.json` | Trà | ✅ |
| Repair | Corrupted data + raw source | Phục hồi từ raw Crossref records | `data/clean/papers_clean_repaired.csv` | Trà | ✅ |
| Orchestration | Toàn bộ artifact trên | `phase1.py` (baseline pipeline), `corruption_flow.py` (corrupt→eval→repair→compare) | `data/results/*.json`, `data/reports/*.md` | Trà | ✅ |
| Jina Embeddings | API key | Jina AI REST API với task-aware routing (retrieval.passage / retrieval.query) | `src/retrieval/jina_embeddings.py` | Trà | ✅ |
| NVIDIA LLM | API key | NVIDIA NIM endpoint qua OpenAI-compatible interface | `src/retrieval/llm.py` (nvidia provider) | Trà | ✅ |
| Stitch UI | Metrics artifacts | RAG quality dashboard hiển thị baseline/corrupted/repaired | `ui/` (HTML/CSS/JS) | Hiếu | ✅ |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| ------------- | --------------- |
| `LLM_PROVIDER` | `nvidia` |
| `LLM_MODEL` | `nvidia/llama-3.1-nemotron-nano-8b-v1` |
| Embedding provider | `jina` (Jina AI REST API) |
| Embedding model | `jina-embeddings-v5-text-small` |
| Số lượng Crossref records | `max_results=24` |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 days (`from-pub-date` filter) |
| Random seed | Không dùng (deterministic: `_evenly_spaced_rows`, fixed `QUESTION_TYPES`) |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

Chỉ giữ lại cách nhóm đã dùng.

```bash
uv sync
```

Hoặc:

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | [Thành công/Thất bại một phần/Thất bại] | [Thời gian]                  | [Artifact hoặc log đã che secret] |
| Corruption flow   | [Thành công/Thất bại một phần/Thất bại] | [Thời gian]                  | [Artifact hoặc log đã che secret] |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| ---------- | ------- |
| Source | Crossref REST API (`https://api.crossref.org/works`) |
| Query | `agentic retrieval augmented generation large language model` |
| Filter | `from-pub-date:2026-02-07,has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-08-06T02:53:02 UTC |
| Số record nhận được | 24 / 24 requested |
| Số record sau parse | 24 |
| Cơ chế retry/backoff | 5 attempts, exponential backoff (2^attempt giây), retry HTTP 429/500/502/503/504 |

### Raw schema — `PaperRecord` (crossref.py)

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| ------- | ------------ | :--------: | -------- | -------------------- |
| `paper_id` | `str` | ✅ | DOI (lowercased) | Bỏ record nếu rỗng |
| `title` | `str` | ✅ | Tiêu đề, đã strip HTML tags | Bỏ record nếu rỗng |
| `summary` | `str` | | Abstract (JATS/XML → plain text) | Gán `""` nếu thiếu |
| `authors` | `list[str]` | | Danh sách tác giả, deduplicated | Gán `[]` nếu thiếu |
| `categories` | `list[str]` | | Chủ đề, fallback → work type | Gán `[work_type]` hoặc `[]` |
| `primary_category` | `str` | | `categories[0]` | Gán `""` nếu thiếu |
| `published` | `str` | | ISO date, ưu tiên: published > published-online > published-print > issued > created | Gán `""` nếu không parse được |
| `updated` | `str` | | ISO date, ưu tiên: indexed > deposited > created | Gán `""` |
| `abs_url` | `str` | ✅ | URL từ item hoặc `https://doi.org/{doi}` | Tạo từ DOI |
| `pdf_url` | `str` | | Link PDF (content-type check) | Gán `""` |
| `comment` | `str` | | Không parse | Luôn `""` |

### Clean schema — DataFrame (cleaning.py → downstream)

**16 columns, 24 rows, 0 dropped**

| Trường | Kiểu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| ------- | ---- | :--------: | -------- | -------------------- |
| `paper_id` | `str` | ✅ | DOI, unique | **Drop record** |
| `title` | `str` | ✅ | Đã normalize whitespace | **Drop record** |
| `summary` | `str` | ✅ | ≥ 100 chars | **Drop record** |
| `authors` | `list[str]` | | List tác giả đã dedup | `[]` |
| `categories` | `list[str]` | | List chủ đề | `[]` |
| `primary_category` | `str` | | `categories[0]` hoặc `""` | `""` |
| `published` | `str` | ✅ | ISO date `YYYY-MM-DD` | **Drop record** nếu không parse được |
| `updated` | `str` | | ISO date | `""` |
| `abs_url` | `str` | | Link DOI | `""` |
| `pdf_url` | `str` | | Link PDF | `""` |
| `comment` | `str` | | Không dùng | `""` |
| `authors_joined` | `str` | | `", "`.join(authors) | `""` |
| `categories_joined` | `str` | | `", "`.join(categories) | `""` |
| `summary_chars` | `int` | | `len(summary)` | 0 |
| `age_days` | `int` | ✅ | `(run_date - published).days` | Luôn ≥0 (invalid date → drop) |
| `text_for_embedding` | `str` | ✅ | `f"Title: {title} \| Authors: {authors_joined} \| Summary: {summary}"` | Tạo từ các trường có sẵn |

### Quy tắc cleaning (đã implement)

| Quy tắc | Quality dimension | Số record bị tác động | Cách xác minh |
| -------- | ----------------- | ---------------------: | ------------- |
| Bỏ record không có `paper_id` | Completeness | 0 | `cleaning_summary.json` |
| Bỏ record không có `title` | Completeness | 0 | `cleaning_summary.json` |
| Bỏ record `len(summary) < 100` | Completeness | 0 | `cleaning_summary.json` |
| Bỏ record `published` không parse được | Validity | 0 | `cleaning_summary.json` |
| Bỏ duplicate `paper_id` (keep first) | Uniqueness | 0 | `cleaning_summary.json` |
| Strip HTML tags + unescape text | Consistency | 24 | Spot-check sample |
| Normalize whitespace (`\s+` → `" "`) | Consistency | 24 | Spot-check sample |
| Deduplicate authors/categories (case-insensitive) | Consistency | — | Spot-check sample |
| Sort by `published` desc, `paper_id` asc | Consistency | 24 | `df.head()` |

Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:

- **`text_for_embedding`**: `f"Title: {title} | Authors: {authors_joined} | Summary: {summary}"` — định dạng structured text giúp embedding model phân biệt rõ các trường. Không bao gồm categories vì categories đã được join vào text không làm tăng chất lượng retrieval đáng kể.
- **Document ID trong ChromaDB**: `f"{paper_id}::{index}"` — kết hợp DOI với row index để đảm bảo uniqueness ngay cả khi cùng paper_id xuất hiện nhiều lần (đã được dedup trước đó).
- **`age_days`**: `(run_date.date() - parsed_published_date).days`. Dùng `pd.to_datetime(value, utc=True)` để parse — mạnh hơn `datetime.strptime` vì hỗ trợ nhiều format. Record có `published` không parse được sẽ bị drop → `age_days` luôn có giá trị hợp lệ.

> 📋 **Data contract đầy đủ:** Xem [`CONTRACT.md`](../../CONTRACT.md) — chứa toàn bộ schema, artifact paths, module responsibilities, và thứ tự bàn giao.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| ---------- | ---------------- |
| Số câu hỏi | 10 |
| Các `question_type` | `summary` (3), `authors` (3), `date` (2), `categories` (2) |
| Ground-truth document ID | `paper_id` của document nguồn (1 doc/câu) |
| Ground-truth answer | `summary`: `first_sentence(summary)`, `authors`: `authors_joined`, `date`: `published`, `categories`: `categories_joined` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | ChromaDB PersistentClient, collection: `papers-baseline`, metric: cosine |
| Retrieval `top_k` | 4 |
| LLM provider/model | [Chưa chạy — cần API key] |
| Test set path | `data/eval/test_set.json` |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:

Test set được build một lần từ clean data và **cố định** (deterministic: `_evenly_spaced_rows` với index cố định, `QUESTION_TYPES` tuple cố định). Khi đánh giá qua 3 trạng thái (baseline → corrupted → repaired), cùng một test set được dùng để đảm bảo **so sánh công bằng**: mọi thay đổi về metric là do thay đổi trong data/index, không phải do test set khác. Đây là nguyên tắc cơ bản của A/B testing trong evaluation.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế | Trạng thái | Ghi chú |
| ------------------------ | ----------------- | :--------: | ------- |
| Raw API response | `data/raw/crossref_response.json` | ✅ Có | 5,850 dòng JSON |
| Raw records | `data/raw/crossref_records.json` | ✅ Có | 24 `PaperRecord` |
| Source manifest | `data/raw/source_manifest.json` | ✅ Có | Metadata lần fetch |
| Cleaned CSV | `data/clean/papers_clean.csv` | ✅ Có | 24 rows × 16 cols |
| Cleaned JSON | `data/clean/papers_clean.json` | ✅ Có | Khớp CSV |
| Cleaning summary | `data/clean/cleaning_summary.json` | ✅ Có | 0 dropped records |
| Embedding manifest | `data/embeddings/papers_embeddings.json` | ✅ Có | 24 documents, ChromaDB backend |
| ChromaDB index | `data/chroma/` | ✅ Có | Collection: `papers-baseline` |
| Evaluation set | `data/eval/test_set.json` | ✅ Có | 10 câu hỏi, 4 types |
| Retrieval smoke test | `data/results/retrieval_smoke_results.json` | ✅ Có | 232 dòng |
| Baseline metrics | `data/results/baseline_metrics.json` | ✅ Có | Jina embeddings baseline |
| Baseline answers | `data/results/baseline_answers.json` | ✅ Có | 10 câu trả lời có judge scores |
| Quality/freshness | `data/quality/` | ✅ Có | baseline + corrupted + repaired + 3 freshness reports |
| Corrupted data | `data/clean/papers_clean_corrupted.*` | ✅ Có | 25 rows (22 + 3 duplicates, 2 dropped) |
| Corruption log | `data/results/corruption_log.json` | ✅ Có | 6 corruptions, 12 affected paper_ids |
| Baseline report | `data/reports/phase1_report.md` | ✅ Có | Phase 1 Markdown report |
| Comparison report | `data/reports/corruption_report.md` | ✅ Có | Baseline vs Corrupted vs Repaired comparison |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` | 1.0000 | Tất cả 10 câu hỏi đều có ground-truth doc trong top-4 retrieved |
| `mean_token_f1`      | 1.0000 | Answer khớp hoàn toàn với ground truth (rule-based extraction) |
| `judge_accuracy`     | 1.0000 | NVIDIA LLM judge xác nhận tất cả câu trả lời đều đúng |
| `mean_judge_score`   | 5.00 | Điểm tối đa từ LLM judge (thang 1-5) |
| Ragas                | N/A (skipped) | Cần `RUN_RAGAS=1` để chạy — chưa được kích hoạt |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| row_count | Completeness | ≥ 1 row | ✅ Pass (24 rows) | `data/quality/baseline.json` |
| paper_id_not_null | Completeness | 0 nulls | ✅ Pass (0 nulls) | `data/quality/baseline.json` |
| paper_id_unique | Uniqueness | 0 duplicates | ✅ Pass (0 duplicates) | `data/quality/baseline.json` |
| title_not_blank | Completeness | 0 blanks | ✅ Pass (0 blanks) | `data/quality/baseline.json` |
| title_not_truncated | Validity | 0 truncated | ✅ Pass (0 truncated) | `data/quality/baseline.json` |
| summary_min_length | Completeness | ≥ 100 chars | ✅ Pass (0 short) | `data/quality/baseline.json` |
| summary_chars_matches_summary | Validity | 0 mismatches | ✅ Pass (0 mismatches) | `data/quality/baseline.json` |
| age_days_non_negative | Validity | ≥ 0 | ✅ Pass (0 negative) | `data/quality/baseline.json` |
| text_for_embedding_not_empty | Completeness | 0 empty | ✅ Pass (0 empty) | `data/quality/baseline.json` |
| text_for_embedding_matches_source_fields | Consistency | 0 mismatches | ✅ Pass (0 mismatches) | `data/quality/baseline.json` |
| text_for_embedding_has_no_noise_tokens | Validity | 0 noisy rows | ✅ Pass (0 noisy) | `data/quality/baseline.json` |
| **Tổng** | — | — | **11/11 passed** | `data/quality/baseline.json` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | `data/clean/papers_clean.csv` (24 records) |
| Timestamp mới nhất       | 2026-08-01 |
| Timestamp cũ nhất        | 2026-02-12 |
| Ngưỡng freshness         | 180 days |
| Trạng thái baseline      | ✅ Fresh (0 stale / 24 total) |
| Lý do                     | Tất cả 24 records đều có `age_days < 180`. Query Crossref đã dùng `from-pub-date` filter 180 ngày, nên freshness được đảm bảo từ nguồn. |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| drop_latest_records | Xóa 2 record có `published` mới nhất | 2 | `row_count` giảm, freshness thay đổi | `corruption_log.json` | Rebuild từ raw |
| blank_summary | Set `summary = ""` trên 2 rows | 2 | `summary_min_length` FAIL | `corruption_log.json` | Rebuild từ raw |
| inject_noise | Thay ~20% token trong `text_for_embedding` bằng noise (XXXX, ###, ERR, ...) | 2 | `text_for_embedding_has_no_noise_tokens` FAIL | `corruption_log.json` | Rebuild từ raw |
| truncate_title | Cắt title còn ~1/3 + dấu `…` | 2 | `title_not_truncated` FAIL | `corruption_log.json` | Rebuild từ raw |
| age_published_dates | Trừ 365 ngày từ `published`, cập nhật `age_days` | 2 | `age_days` tăng, freshness degraded | `corruption_log.json` | Rebuild từ raw |
| duplicate_rows | Nhân đôi 2 rows (concat) | 2 | `paper_id_unique` FAIL | `corruption_log.json` | Dedup từ raw |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: ✅ Có
- Nhận xét: Log ghi đầy đủ 6 loại corruption, 12 affected paper_ids, description, và tham số. Tổng: 24 rows ban đầu → 25 rows corrupted (22 + 3 từ duplicate, 2 dropped = net +1).

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:

Repair strategy (`_repair_from_raw` trong `corruption_flow.py`) không patch từng dòng bị corrupt. Thay vào đó, nó reload toàn bộ raw records từ `data/raw/crossref_records.json` và chạy lại `build_clean_dataframe()` — tức rebuild từ trusted source. Cách này đảm bảo: (1) dữ liệu được tái tạo từ nguồn gốc đã lưu, không phụ thuộc vào state hiện tại của corrupted DataFrame; (2) các record bị drop do corruption được khôi phục; (3) schema, cleaning rules, và derived fields (`text_for_embedding`, `age_days`) được áp dụng nhất quán. Đây là nguyên tắc "reprocess from source", không phải "patch what's broken".

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate` | 1.0000 | 0.8000 | 1.0000 | -0.2000 (↓20%) | 100% | Corruption làm mất retrieval hit |
| `mean_token_f1` | 1.0000 | 0.8327 | 1.0000 | -0.1673 (↓17%) | 100% | Noise + blank summary giảm F1 |
| `judge_accuracy` | 1.0000 | 0.8000 | 1.0000 | -0.2000 (↓20%) | 100% | Judge phát hiện sai do thiếu context |
| `mean_judge_score` | 5.00 | 4.30 | 5.00 | -0.70 (↓14%) | 100% | Điểm giảm nhẹ trên câu trả lời sai |
| Quality checks | 11/11 ✅ | 7/11 ❌ | 11/11 ✅ | 4 checks FAIL | 100% | Noise + blank + truncate + duplicate |
| Freshness status | ✅ Fresh | ❌ Stale | ✅ Fresh | Có stale rows | 100% | Age corruption → freshness degraded |

Nêu ít nhất hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifacts:

1. **blank_summary + inject_noise → text_for_embedding hỏng → retrieval_hit_rate giảm từ 1.0 → 0.8.** Khi `text_for_embedding` bị corrupt (summary rỗng hoặc chứa noise tokens), vector embedding không còn đại diện chính xác cho nội dung paper → semantic search trả về sai document cho 2/10 câu hỏi. Bằng chứng: `data/results/corrupted_answers.json` cho thấy 2 câu hỏi có `retrieval_hit: false`.

2. **Rebuild từ raw source → toàn bộ metrics phục hồi 100% về baseline.** Repair strategy (`_repair_from_raw`) reload toàn bộ raw records và chạy lại `build_clean_dataframe()`, không patch từng dòng. Kết quả: `repaired_metrics.json` khớp hoàn toàn với `baseline_metrics.json` (hit_rate=1.0, f1=1.0, judge=1.0, score=5.0, quality=11/11).

Không kết luận corruption “có tác động” nếu số liệu không cho thấy thay đổi. Nếu kết quả khác kỳ vọng, mô tả giả thuyết và cách nhóm đã kiểm tra.

## 11. Vấn đề tích hợp quan trọng

Mô tả một vấn đề phát sinh khi ghép các module trong pipeline và cách nhóm xử lý:

- **Triệu chứng:** [Lỗi hoặc kết quả sai.]
- **Nguyên nhân:** [Root cause.]
- **Cách xử lý:** [Thay đổi đã thực hiện.]
- **Cách xác minh:** [Lệnh và artifact.]

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| [Giới hạn]          | [Ảnh hưởng] | [Đề xuất]                              |
| [Giới hạn]          | [Ảnh hưởng] | [Đề xuất]                              |

## 13. Checklist trước khi nộp

- [ ] Thông tin nhóm và repository chính xác.
- [ ] Phân công khớp với module, artifact và kết quả thực tế.
- [ ] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [ ] Baseline, corrupted và repaired dùng cùng evaluation set.
- [ ] Bảng metrics khớp với các file trong `data/results/`.
- [ ] Quality/freshness conclusions khớp với `data/quality/`.
- [ ] Các đường dẫn báo cáo và artifact truy cập được.
- [ ] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [ ] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
