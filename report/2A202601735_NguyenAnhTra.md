# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Anh Trà |
| MSSV | 2A202601735 |
| Khóa/Lớp | K3 |
| Tên nhóm | sacadingsacadung |
| Vai trò chính | Corruption, Observability, Pipeline Orchestration và Multi-Provider Owner |
| Repository | https://github.com/ashura102938475/K3_Day10_sacadingsacadung |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Corruption engine | `src/ingestion/corruption.py` | Clean DataFrame (24 rows × 16 cols) | Corrupted DataFrame + `corruption_log.json` (6 loại corruption, 12 affected paper_ids) | Hoàn thành |
| Targeted repair | `src/ingestion/repair.py` | Corrupted DataFrame + good baseline + corruption log | Repaired DataFrame + `repair_log.json` | Hoàn thành |
| Data quality checks | `src/observability/quality.py` | DataFrame bất kỳ | 11 quality checks (completeness, uniqueness, validity, consistency) + freshness report | Hoàn thành |
| Markdown reporting | `src/observability/reporting.py` | Metrics, quality, freshness artifacts | `phase1_report.md`, `corruption_report.md` | Hoàn thành |
| Baseline pipeline | `src/pipelines/phase1.py` | Raw Crossref records | Toàn bộ baseline artifacts (clean → embed → eval → quality → report) | Hoàn thành |
| Corruption flow | `src/pipelines/corruption_flow.py` | Clean baseline + corruption log | Corrupt → re-eval → repair → compare (full comparison pipeline) | Hoàn thành |
| Jina embeddings provider | `src/retrieval/jina_embeddings.py` | Text + JINA_API_KEY | 1024-dim normalized vectors với task-aware routing (passage/query) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Multi-provider LLM config | `src/core/config.py` — 7 providers (NVIDIA, Gemini, OpenAI, Anthropic, OpenRouter, Ollama, Custom) | Settings dataclass với credential validation, `require_llm_credentials()`, `require_embedding_credentials()` |
| NVIDIA LLM provider | `src/retrieval/llm.py` — NVIDIA NIM endpoint qua OpenAI-compatible interface | LLM judge và agent chạy được trên NVIDIA backend |
| Embedding factory | `src/retrieval/embeddings.py` — `create_embeddings()` dispatch Jina vs local | Hiếu dùng factory này để build index cho cả 3 data state |
| ChromaDB index integration | `src/retrieval/index.py` — `LocalEmbeddingIndex.build()` | Index hoạt động với cả Jina và local embeddings |
| Evaluation pipeline hardening | `src/evaluation/metrics.py` — `evaluate_pipeline()`, judge fallback, Ragas integration | Đảm bảo eval chạy được qua 3 state với cùng test set |
| Project scaffolding | `.env.example`, `pyproject.toml` | Cấu hình chuẩn cho cả nhóm |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Thiết kế và implement 6 corruption scenarios | `corruption.py`, `data/results/corruption_log.json` | 6 corruption types: drop_latest_records, blank_summary, inject_noise, truncate_title, age_published_dates, duplicate_rows | `cat data/results/corruption_log.json \| python -m json.tool` |
| Implement targeted repair từ corruption log | `repair.py`, `data/results/repair_log.json` | Repair chỉ chạm affected paper_ids, không thay thế toàn bộ DataFrame | So sánh `before.rows`/`after.rows` trong repair log |
| Implement 11 data quality checks | `quality.py`, `data/quality/baseline.json`, `corrupted.json`, `repaired.json` | 11 checks: row_count, paper_id_not_null, paper_id_unique, title_not_blank, title_not_truncated, summary_min_length, summary_chars_matches_summary, age_days_non_negative, text_for_embedding_not_empty, text_for_embedding_matches_source_fields, text_for_embedding_has_no_noise_tokens | `cat data/quality/baseline.json` — 11/11 passed |
| Implement freshness monitoring | `quality.py` — `build_freshness_report()`, `data/quality/freshness_report.json` | Freshness report với threshold 180 days, latest/oldest timestamp, stale ratio | `cat data/quality/freshness_report.json` |
| Orchestrate baseline pipeline | `phase1.py`, `script/run_phase1.py` | End-to-end: raw → clean → embed → eval → quality → freshness → report | `uv run python script/run_phase1.py` |
| Orchestrate corruption → repair → compare flow | `corruption_flow.py`, `script/run_corruption_flow.py` | Corrupt → re-index → re-eval → quality/freshness → repair → re-eval → comparison report | `uv run python script/run_corruption_flow.py` |
| Jina Embeddings API integration | `jina_embeddings.py` | `JinaEmbeddings` class với batch processing (max 64/batch), task-aware routing (`retrieval.passage` cho docs, `retrieval.query` cho queries), normalized output | Kiểm tra `data/embeddings/papers_embeddings.json` — 24 vectors, 1024 dims |
| Multi-provider LLM support | `config.py`, `llm.py` | 7 LLM providers (NVIDIA, Gemini, OpenAI, Anthropic, OpenRouter, Ollama, Custom) + 2 embedding providers (Jina, local) | Chạy eval với `LLM_PROVIDER=nvidia` — judge accuracy = 1.0 |

Output tiêu biểu của phần việc là toàn bộ corruption → repair → comparison pipeline: từ clean baseline 24 rows, áp dụng 6 loại corruption có chủ đích (mỗi loại ảnh hưởng 2 rows), đánh giá lại toàn bộ metrics (retrieval hit rate giảm 1.0 → 0.8, quality 11/11 → 7/11), repair từ raw source records, và xác minh tất cả metrics phục hồi 100% về baseline. Corruption log và repair log đều có thể audit độc lập — mỗi corruption ghi rõ affected paper_ids, dataset impact, rag impact, và repair strategy.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần chứng minh được rằng data corruption ảnh hưởng trực tiếp đến chất lượng RAG agent và data observability có thể phát hiện, khoanh vùng chính xác từng loại hư hỏng. Ngoài ra, repair phải khôi phục được dữ liệu từ trusted source (raw Crossref records) thay vì chỉ patch cục bộ — đảm bảo tính tái lập và audit được. Cuối cùng, hệ thống cần hỗ trợ nhiều LLM/embedding provider để không bị khóa cứng vào một vendor.

### Cách triển khai

**Corruption engine** (`corruption.py`) áp dụng 6 loại corruption tuần tự, mỗi loại chọn đúng 2 rows không trùng lặp (dùng `random.Random(42)` để deterministic). Thứ tự áp dụng được tính toán để các corruption không ghi đè lên nhau: drop trước (thay đổi index), sau đó blank summary → noise → truncate → age → duplicate. Sau khi áp dụng blank và truncate, `text_for_embedding` được rebuild từ source fields trước khi inject noise — đảm bảo noise là corruption độc lập, không bị ảnh hưởng bởi blank/truncate. Mỗi corruption ghi vào log đầy đủ: tên corruption, count, affected_paper_ids, description, dataset_impact, rag_impact, và repair_strategy.

**Repair strategy** (`repair.py`) không rebuild toàn bộ từ raw (cách đó đúng nhưng không chứng minh được targeted repair). Thay vào đó, nó đọc corruption log, lấy danh sách `paper_id` bị ảnh hưởng cho từng loại corruption, và chỉ sửa đúng những trường bị hỏng: duplicate → xóa bản sao, drop → thêm lại rows từ good baseline, blank_summary → khôi phục `summary` + `summary_chars` + `text_for_embedding`, noise → khôi phục `text_for_embedding`, truncate → khôi phục `title` + `text_for_embedding`, age → khôi phục `published` + `age_days`. Các record không bị ảnh hưởng được giữ nguyên — điều này chứng minh repair có tính targeted (chỉ sửa đúng thứ hỏng).

**Quality checks** (`quality.py`) thực hiện 11 checks phân bố đều 4 quality dimensions: Completeness (row_count, paper_id_not_null, title_not_blank, summary_min_length, text_for_embedding_not_empty), Uniqueness (paper_id_unique), Validity (title_not_truncated, summary_chars_matches_summary, age_days_non_negative, text_for_embedding_has_no_noise_tokens), Consistency (text_for_embedding_matches_source_fields). Mỗi check trả về structured result với check name, passed/failed, quality dimension, observed value, expected value. Freshness report đo `age_days` so với threshold 180 ngày, tính latest/oldest published timestamp và stale ratio.

**Pipeline orchestration** (`phase1.py`, `corruption_flow.py`) đảm bảo thứ tự thực thi đúng: phase1 chạy baseline end-to-end (raw → clean → embed → eval → quality → report), corruption_flow chạy corrupt → re-eval → repair → re-eval → compare. Cả hai đều có early validation (kiểm tra artifact tồn tại trước khi chạy) và in rõ output paths sau khi hoàn thành.

**Jina embeddings** (`jina_embeddings.py`) implement LangChain `Embeddings` interface với task-aware routing: `retrieval.passage` cho document embedding, `retrieval.query` cho query embedding. Batch processing (max 64 texts/request) để tránh timeout, response validation (số lượng vector khớp số input), và normalized output (cosine similarity-ready).

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Clean DataFrame (16 cols, 24 rows); JINA_API_KEY; NVIDIA_API_KEY; corruption_log.json; evaluation test set |
| Output | Corrupted/Repaired DataFrames + CSV/JSON; corruption_log.json; repair_log.json; 3 bộ quality reports; 3 freshness reports; 3 bộ metrics + answers; phase1_report.md; corruption_report.md |
| Module phụ thuộc | `core.config`, `core.utils`, `evaluation.metrics`, `evaluation.testset`, `ingestion.cleaning`, `ingestion.crossref`, `retrieval.index`, `retrieval.embeddings`, `retrieval.llm`, `retrieval.qa` |
| Module sử dụng output | Dashboard API (`src/dashboard_api/app.py`) đọc quality + metrics artifacts; UI (`ui/`) hiển thị comparison; cả nhóm dùng corruption_log.json để verify repair |
| Điều kiện lỗi cần xử lý | Thiếu JINA_API_KEY → embedding fail; thiếu NVIDIA_API_KEY → judge fallback về heuristic token-F1; corruption trên DataFrame rỗng; repair với paper_id không tồn tại trong good baseline; thiếu baseline_metrics hoặc test_set khi chạy corruption_flow |

### Cách xác minh

```bash
# Baseline pipeline
uv run python script/run_phase1.py

# Corruption flow
uv run python script/run_corruption_flow.py

# Kiểm tra artifacts
cat data/results/corruption_log.json | python -m json.tool
cat data/results/repair_log.json | python -m json.tool
cat data/quality/baseline.json | python -m json.tool
cat data/quality/corrupted.json | python -m json.tool
cat data/quality/repaired.json | python -m json.tool
```

- **Kết quả mong đợi:** Baseline: 11/11 quality checks pass, retrieval_hit_rate=1.0, 0 stale rows. Corrupted: 7/11 quality checks pass (4 FAIL: uniqueness, summary, title, noise), retrieval_hit_rate=0.8, 2 stale rows. Repaired: 11/11 quality checks pass, retrieval_hit_rate=1.0, 0 stale rows — tất cả metrics khớp baseline.
- **Kết quả thực tế:** Baseline metrics đạt 1.0 toàn bộ. Corrupted: hit_rate=0.8, token_f1=0.8327, judge_accuracy=0.8, score=4.3, quality=7/11. Repaired: khớp hoàn toàn baseline (hit_rate=1.0, f1=1.0, judge=1.0, score=5.0, quality=11/11).
- **Artifact/log:** `data/results/corruption_log.json`, `data/results/repair_log.json`, `data/quality/*.json`, `data/results/baseline_metrics.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi thiết kế corruption engine, có hai hướng: (a) áp dụng từng corruption độc lập lên clean data (mỗi corruption tạo một bản corrupted riêng), hoặc (b) áp dụng tuần tự tất cả corruption lên cùng một DataFrame. Cách (a) cho phép đo tác động riêng của từng corruption (ablation study) nhưng không phản ánh thực tế — dữ liệu thật thường bị nhiều loại hư hỏng cùng lúc. Cách (b) giống thực tế hơn nhưng khó phân rã metric delta theo từng corruption.
- **Các phương án đã cân nhắc:** (a) Ablation: 6 lần chạy riêng, mỗi lần 1 corruption → 6 bộ metrics để so sánh. (b) Cumulative: áp dụng tuần tự 6 corruption lên cùng DataFrame → 1 bộ metrics duy nhất. (c) Hybrid: vừa cumulative vừa ghi log chi tiết paper_ids để có thể truy vết ngược.
- **Phương án đã chọn:** (c) Hybrid — cumulative corruption với structured log. Mỗi corruption ghi rõ affected_paper_ids và không chọn rows đã bị corruption trước đó (trừ noise được phép overlap với blank vì bản chất khác nhau). Corruption log đóng vai trò "ground truth" cho repair: repair chỉ sửa đúng những gì log ghi nhận.
- **Lý do:** Cumulative approach phản ánh thực tế hơn (dữ liệu thường hỏng nhiều thứ cùng lúc). Structured log với paper_ids cho phép audit độc lập và targeted repair — không cần rebuild toàn bộ từ raw. Nếu cần ablation study sau này, có thể chạy từng corruption riêng dựa trên cùng codebase và seed cố định.
- **Bằng chứng quyết định phù hợp:** Repair log cho thấy repair chỉ chạm 12 affected paper_ids (trong tổng số 24), các record không bị ảnh hưởng được giữ nguyên. Sau repair, toàn bộ metrics phục hồi 100% về baseline — chứng minh corruption log đã khoanh vùng chính xác và repair strategy đủ chính xác để không làm hỏng dữ liệu tốt.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Khi chạy corruption flow, `text_for_embedding` của các rows bị blank_summary và truncate_title không được rebuild trước khi inject noise. Kết quả: noise injection ghi đè lên text_for_embedding đã được rebuild, hoặc text_for_embedding vẫn giữ giá trị cũ (từ clean data) trong khi summary đã bị blank.
- **Lệnh hoặc bước tái hiện:** Chạy `uv run python script/run_corruption_flow.py`, sau đó kiểm tra `data/clean/papers_clean_corrupted.json` — các rows bị blank_summary có `summary=""` nhưng `text_for_embedding` vẫn chứa summary cũ.
- **Nguyên nhân gốc:** Thứ tự thực thi trong `corrupt_clean_dataframe`: blank và truncate được áp dụng trước, nhưng `text_for_embedding` chỉ được rebuild một lần ở cuối hàm. Nếu noise injection chạy sau rebuild, nó sẽ ghi đè. Nếu rebuild không chạy, derived field không đồng bộ với source fields.
- **Cách xử lý:** Restructure thứ tự trong `corrupt_clean_dataframe()`: (1) áp dụng blank_summary và truncate_title → (2) rebuild `text_for_embedding` cho các affected paper_ids (dùng `_rebuild_embedding_text()`) → (3) inject noise tokens vào `text_for_embedding` (chỉ thay đổi token, không rebuild lại từ source) → (4) duplicate rows. Cách này đảm bảo noise là corruption cuối cùng trên `text_for_embedding` và các corruption trước đó đã được phản ánh đúng trong derived field.
- **Cách xác minh sau khi sửa:** Chạy lại corruption flow, kiểm tra corrupted JSON: rows bị blank_summary có `text_for_embedding` chứa `Summary: ` (rỗng), rows bị truncate có title ngắn trong embedding text, rows bị noise có token như `XXXX`, `###` xen kẽ — mỗi corruption độc lập và không ghi đè lên nhau. Quality check `text_for_embedding_matches_source_fields` phát hiện đúng 2 mismatches (noise rows, đã được loại trừ khỏi check vì intentional).
- **Điều học được:** Khi implement multi-step corruption trên derived fields, thứ tự thực thi và synchronization giữa source fields và derived fields là critical. Derived field phải được rebuild sau mỗi corruption ảnh hưởng đến source fields, và intentional corruption (như noise) phải là bước cuối cùng trên field đó. Nếu không, chất lượng corruption không được đảm bảo và quality checks có thể cho false positive/negative.

## 7. Hiểu biết về luồng end-to-end

1. Crossref API trả về 24 papers dạng JSON thô → `crossref.py` parse thành `PaperRecord` (DOI, title, summary, authors, categories, published, v.v.) → `cleaning.py` chuẩn hóa (strip HTML, normalize whitespace, validate required fields, dedup) → DataFrame 16 columns → `text_for_embedding` được tạo từ template `Title: {title} | Authors: {authors_joined} | Summary: {summary}` → Jina API embed thành 1024-dim vectors → ChromaDB index với cosine metric.

2. Test set gồm 10 câu hỏi deterministic (3 summary, 3 authors, 2 date, 2 categories), mỗi câu có ground-truth `paper_id` và ground-truth answer. Retrieval hit kiểm tra ground-truth doc có trong top-k không. Token F1 so sánh overlap giữa predicted answer và ground truth. LLM judge (NVIDIA Nemotron) chấm điểm 1-5 và xác nhận correct/incorrect. Cả 3 metric đều được lưu vào JSON để audit.

3. Quality checks đo chất lượng dữ liệu tại một thời điểm (completeness, uniqueness, validity, consistency) — trả lời câu hỏi "dữ liệu có đúng không?". Freshness monitoring đo tuổi dữ liệu theo thời gian (stale ratio, latest/oldest timestamp) — trả lời câu hỏi "dữ liệu có còn mới không?". Trong bài lab, quality checks phát hiện các corruption như blank summary, duplicate, noise; freshness phát hiện aged dates và drop latest records.

4. Cùng test set cho cả 3 trạng thái là nguyên tắc A/B testing cơ bản: nếu thay đổi test set, không thể phân biệt được metric thay đổi là do data corruption hay do câu hỏi khác. Test set cố định đảm bảo biến độc lập duy nhất là trạng thái dữ liệu (baseline → corrupted → repaired), mọi delta về metric đều quy được về data change.

5. Repair thành công khi: (a) `repair_log.json` xác nhận tất cả 6 corruption types đã được xử lý (rows added/removed, fields restored), (b) quality checks trở về 11/11 (từ 7/11), (c) freshness trở về 0 stale rows (từ 2/24), (d) 4 agent metrics (retrieval_hit_rate, mean_token_f1, judge_accuracy, mean_judge_score) khớp chính xác baseline. Bằng chứng: `data/results/repaired_metrics.json` ≈ `data/results/baseline_metrics.json`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.8000 | 1.0000 | Mất 2/10 retrieval hit — đúng bằng số rows bị blank_summary + noise (embedding text hỏng → vector sai → semantic search trả sai doc) |
| `mean_token_f1` | 1.0000 | 0.8327 | 1.0000 | F1 giảm 0.1673 do answer trên wrong document khác ground truth |
| `judge_accuracy` | 1.0000 | 0.8000 | 1.0000 | Judge accuracy giảm 20pp — khớp với retrieval hit rate giảm, cho thấy judge phụ thuộc vào retrieval quality |
| `mean_judge_score` | 5.00 | 4.30 | 5.00 | Giảm 0.70 trên thang 5 — judge vẫn cho điểm partial credit trên câu sai |
| Quality checks | 11/11 | 7/11 | 11/11 | 4 checks FAIL: paper_id_unique (duplicate), summary_min_length (blank), title_not_truncated (truncate), text_for_embedding_has_no_noise_tokens (noise) |
| Freshness status | Fresh, 0 stale | Stale, 2/24 | Fresh, 0 stale | 2 rows bị age_published_dates có age_days vượt threshold 180 → stale ratio = 8.33% |

### Kết luận từ số liệu

1. **blank_summary + inject_noise → text_for_embedding hỏng → retrieval_hit_rate giảm 1.0 → 0.8 → judge_accuracy giảm 1.0 → 0.8.** Đây là chuỗi nhân quả rõ nhất: 2 rows bị corruption trên `text_for_embedding` (1 blank summary, 1 noise injection — không trùng paper_id) dẫn đến vector embedding sai lệch, semantic search trả về wrong document cho 2/10 câu hỏi, kéo theo answer sai và judge đánh giá incorrect. Bằng chứng: `data/results/corrupted_answers.json` cho thấy đúng 2 câu có `retrieval_hit: false`, và `data/results/corruption_log.json` xác nhận 2 affected paper_ids từ blank_summary + inject_noise.

2. **Targeted repair từ corruption log → quality 7/11 → 11/11, freshness stale → fresh, toàn bộ agent metrics phục hồi 100%.** Repair chỉ khôi phục đúng 12 affected paper_ids được ghi trong corruption log (không rebuild toàn bộ), chứng minh rằng corruption log đã khoanh vùng chính xác và repair strategy đủ chính xác. Bằng chứng: `data/results/repair_log.json` — `before.rows: 25, after.rows: 24`, `targeted_unique_records: 12`; `data/results/repaired_metrics.json` khớp từng metric với `baseline_metrics.json`.

Corruption ảnh hưởng rõ nhất là **blank_summary** và **inject_noise** vì cả hai trực tiếp làm hỏng `text_for_embedding` — trường đầu vào duy nhất cho embedding model. Khi vector embedding sai, toàn bộ downstream pipeline (retrieval → answer generation → judge evaluation) bị ảnh hưởng dây chuyền. Ngược lại, `duplicate_rows` tuy làm quality FAIL (uniqueness) nhưng không làm thay đổi embedding của các record gốc — tác động đến retrieval ít hơn (chỉ crowding top-k). `drop_latest_records` ảnh hưởng retrieval hit nếu câu hỏi eval nhắm đúng vào record bị drop, nhưng trong thí nghiệm này, 2 record bị drop không phải là ground-truth của câu hỏi nào.

Kết quả khác kỳ vọng: corrupted dataset có 25 rows (nhiều hơn baseline 24), tưởng như row_count tăng. Thực tế, drop đã xóa 2 rows nhưng duplicate thêm 2 rows → net +1. Chỉ quan sát row_count sẽ bỏ sót lỗi — uniqueness check (`paper_id_unique`) mới phát hiện đúng: 25 rows nhưng chỉ có 22 unique paper_ids. Điều này khẳng định giá trị của multi-dimensional quality checks: mỗi dimension (completeness, uniqueness, validity, consistency) bắt một loại lỗi khác nhau.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data contract và artifact immutability là nền tảng của reproducible pipeline.** Mọi module trong pipeline đọc/ghi artifact qua paths xác định rõ trong `Settings`, không module nào tự ý thay đổi schema hoặc đường dẫn. Điều này giúp corruption flow có thể load baseline artifacts, áp dụng corruption, và so sánh kết quả mà không sợ inconsistent state.

2. **Observability cần multi-dimensional: quality checks + freshness + metrics + structured logs.** Không một metric đơn lẻ nào đủ để phát hiện tất cả vấn đề. Quality checks bắt blank summary và duplicate nhưng không bắt được stale data; freshness bắt aged dates nhưng không bắt được noise; metrics bắt tác động end-to-end nhưng không chỉ ra root cause. Chỉ khi kết hợp cả 4 tín hiệu, ta mới có bức tranh đầy đủ: cái gì hỏng → ảnh hưởng thế nào → repair ra sao.

3. **Corruption log là "single source of truth" cho repair — không phải data diff.** Thay vì diff corrupted vs baseline để tìm sự khác biệt (cách này mong manh vì không phân biệt được intentional corruption vs legitimate data variation), corruption log ghi lại chính xác những gì đã bị thay đổi. Repair chỉ cần đọc log và sửa đúng những gì log mô tả — an toàn, chính xác, và audit được.

### Nếu có thêm thời gian

Tôi sẽ implement **ablation study mode** trong corruption flow: thay vì áp dụng tất cả 6 corruption cùng lúc, chạy từng corruption riêng biệt (6 lần) và đo metric delta cho từng loại. Điều này cho phép định lượng chính xác mỗi corruption gây bao nhiêu % degradation — hiện tại ta chỉ biết cumulative impact là -20% hit rate, nhưng không biết blank_summary gây bao nhiêu, noise gây bao nhiêu. Cách đo: thêm flag `--ablation` vào `corruption_flow.py`, mỗi lần chỉ bật 1 corruption type, chạy full eval, và tổng hợp thành bảng so sánh 6 dòng. Kết quả sẽ có giá trị cao cho việc prioritize data quality fixes trong production.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Anh Trà

**Ngày xác nhận:** 2026-08-06
