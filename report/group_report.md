# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung |
| ----------------- | -------- |
| Khóa/Lớp          | K3 |
| Tên nhóm          | sacadingsacadung |
| Repository         | https://github.com/ashura102938475/K3_Day10_sacadingsacadung |
| Ngày hoàn thành   | [YYYY-MM-DD] |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Anh Trà | 2A202601735 | Upstream Data Owner | `crossref.py` ✅, `cleaning.py` ✅, `corruption.py` 🔧 |
| 2 | Nguyễn Chí Hiếu | 2A202601931 | Downstream Pipeline & Eval Owner | `testset.py` ✅, `embeddings.py` ✅, `index.py` ✅, `agent.py` ✅, `qa.py` ✅, `quality.py` 🔧, `reporting.py` 🔧, `phase1.py` 🔧, `corruption_flow.py` 🔧 |

> ✅ = đã implement | 🔧 = đang/cần implement

## 2. Tóm tắt kết quả

Viết từ 150–250 từ, trả lời ngắn gọn:

- Nhóm đã hoàn thành những phần nào?
- Baseline pipeline đã tạo ra các artifact nào?
- Corruption nào ảnh hưởng rõ nhất đến data quality hoặc agent?
- Repair đã phục hồi được chỉ số nào?
- Blocker hoặc giới hạn quan trọng nhất còn lại là gì?

**Tóm tắt của nhóm:**

[Viết phần tóm tắt tại đây.]

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
| Observability | `data/clean/papers_clean.csv` | Great Expectations quality checks, freshness report | `data/quality/`, `data/quality/freshness_report.json` | Hiếu | 🔧 |
| Corruption | `data/clean/papers_clean.csv` | Mô phỏng các dạng corruption (null, duplicate, noise, drift) | `data/clean/papers_clean_corrupted.csv`, `data/results/corruption_log.json` | Trà | 🔧 |
| Repair | Corrupted data + nguồn clean | Phục hồi từ dữ liệu nguồn đáng tin cậy | `data/clean/papers_clean_repaired.csv` | Hiếu | 🔧 |
| Orchestration | Toàn bộ artifact trên | `phase1.py` (baseline pipeline), `corruption_flow.py` (corrupt→eval→repair→compare) | `data/results/*.json`, `data/reports/*.md` | Hiếu | 🔧 |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| ------------- | --------------- |
| `LLM_PROVIDER` | [Chưa chạy LLM — sẽ dùng `gemini` hoặc `nvidia`] |
| `LLM_MODEL` | [Tùy provider] |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
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
| Baseline metrics | `data/results/baseline_metrics.json` | ❌ Thiếu | Cần `phase1.py` |
| Baseline answers | `data/results/baseline_answers.json` | ❌ Thiếu | Cần `phase1.py` |
| Quality/freshness | `data/quality/` | ❌ Thiếu | Cần `quality.py` |
| Corrupted data | `data/clean/papers_clean_corrupted.*` | ❌ Thiếu | Cần `corruption.py` |
| Corruption log | `data/results/corruption_log.json` | ❌ Thiếu | Cần `corruption.py` |
| Baseline report | `data/reports/phase1_report.md` | ❌ Thiếu | Cần `reporting.py` |
| Comparison report | `data/reports/corruption_report.md` | ❌ Thiếu | Cần `corruption_flow.py` |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     [Giá trị] | [Ý nghĩa trong kết quả của nhóm]  |
| `mean_token_f1`      |     [Giá trị] | [Diễn giải]                           |
| `judge_accuracy`     |     [Giá trị] | [Diễn giải]                           |
| `mean_judge_score`   |     [Giá trị] | [Diễn giải]                           |
| Ragas, nếu có        | [Giá trị/N/A] | [Diễn giải hoặc lý do không chạy] |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| [Tên check] | [Dimension]       | [Ngưỡng]         | [Pass/Fail + giá trị] | [Artifact]   |
| [Tên check] | [Dimension]       | [Ngưỡng]         | [Pass/Fail + giá trị] | [Artifact]   |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | [Dataset/index/artifact]            |
| Timestamp mới nhất       | [Giá trị]                         |
| Ngưỡng freshness         | [Giá trị]                         |
| Trạng thái baseline      | [Fresh/Stale/Unknown]               |
| Lý do                     | [Giải thích dựa trên số liệu] |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| [Loại corruption] | [Mô tả]  |          [Số lượng] | [Kỳ vọng]              | [Artifact/metric]     | [Cách repair] |
| [Loại corruption] | [Mô tả]  |          [Số lượng] | [Kỳ vọng]              | [Artifact/metric]     | [Cách repair] |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: [Có/Thiếu]
- Nhận xét: [Log có đủ loại corruption, record bị tác động và tham số hay không?]

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:

[Giải thích tại đây.]

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |      [ ] |       [ ] |      [ ] |                      [ ] |             [ ] | [Nhận xét] |
| `mean_token_f1`        |      [ ] |       [ ] |      [ ] |                      [ ] |             [ ] | [Nhận xét] |
| `judge_accuracy`       |      [ ] |       [ ] |      [ ] |                      [ ] |             [ ] | [Nhận xét] |
| `mean_judge_score`     |      [ ] |       [ ] |      [ ] |                      [ ] |             [ ] | [Nhận xét] |
| Quality checks pass/fail |      [ ] |       [ ] |      [ ] |                      [ ] |             [ ] | [Nhận xét] |
| Freshness status         |      [ ] |       [ ] |      [ ] |                      [ ] |             [ ] | [Nhận xét] |

Nêu ít nhất hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifacts:

1. [Corruption/data change] → [quality/freshness signal] → [retrieval/answer metric].
2. [Repair action] → [quality/freshness recovery] → [agent metric recovery hoặc lý do chưa recovery].

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
