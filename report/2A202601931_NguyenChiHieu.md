# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Chí Hiếu |
| MSSV | 2A202601931 |
| Khóa/Lớp | K3 |
| Tên nhóm | sacadingsacadung |
| Vai trò chính | Ingestion, Retrieval, Evaluation và UI Owner |
| Repository | https://github.com/ashura102938475/K3_Day10_sacadingsacadung |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Crossref ingestion | `src/ingestion/crossref.py` | Crossref REST API | Raw response, 24 raw records và source manifest trong `data/raw/` | Hoàn thành |
| Cleaning và data modeling | `src/ingestion/cleaning.py` | `data/raw/crossref_records.json` | `papers_clean.csv/json`, cleaning summary, schema 16 trường | Hoàn thành |
| Evaluation set | `src/evaluation/testset.py` | Cleaned dataset | `data/eval/test_set.json` gồm 10 câu thuộc 4 loại | Hoàn thành |
| Embedding và retrieval | `src/retrieval/embeddings.py`, `index.py`, `qa.py`, `agent.py`, `llm.py` | `text_for_embedding`, câu hỏi và cấu hình provider | Jina embeddings 1024 chiều, Chroma index, retrieval và grounded answer | Hoàn thành |
| Dashboard và chatbot | `ui/`, `src/dashboard_api/app.py` | Metrics, quality artifacts và ba Chroma collection | Dashboard tiếng Việt, slide thuyết trình, chatbot ba trạng thái | Hoàn thành |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Thu thập và parse Crossref | `crossref.py`, `data/raw/source_manifest.json` | Nhận và parse đủ 24/24 bài báo | Đối chiếu `requested_rows`, `received_items`, `parsed_records` |
| Chuẩn hóa dữ liệu | `cleaning.py`, `data/clean/cleaning_summary.json` | 24 dòng × 16 trường; không có dòng bị loại ở snapshot hiện tại | Kiểm tra cleaning summary và clean JSON |
| Tạo embedding/index | `embeddings.py`, `index.py`, `papers_embeddings.json` | Jina `jina-embeddings-v5-text-small`, vector 1024 chiều, Chroma cosine | Kiểm tra embedding manifest và query index |
| Xây dựng bộ eval | `testset.py`, `data/eval/test_set.json` | 10 câu: summary ×3, authors ×3, date ×2, categories ×2 | Đếm `question_type` trong artifact |
| Hoàn thiện UI demo | `ui/index.html`, `ui/app.js`, `ui/styles.css` | Dashboard, chatbot ba mode, Markdown/table renderer và 9 slide | `npm --prefix ui run check`; mở `http://127.0.0.1:8000/ui/` |

Output tiêu biểu của phần việc là pipeline baseline có khả năng truy vết từ 24 raw records đến clean dataset, Jina/Chroma index và bộ eval 10 câu. Trên cùng nền dữ liệu đó, dashboard thể hiện được sự khác biệt giữa baseline, corrupted và repaired mà không phải chỉnh tay số liệu trong UI.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Nguồn Crossref có cấu trúc không đồng nhất: abstract có thể chứa JATS/XML, tác giả và category là danh sách, ngày xuất bản có nhiều trường fallback. Retrieval chỉ đáng tin khi các trường này được chuẩn hóa thành một contract ổn định, document identity không đổi và embedding của passage/query dùng đúng provider. Ngoài ra, kết quả cần được đánh giá trên một test set cố định và trình bày bằng artifact có thể kiểm tra lại.

### Cách triển khai

Ingestion gọi Crossref với retry/backoff cho HTTP 429 và lỗi 5xx, lưu nguyên response trước khi parse thành `PaperRecord`. Cleaning loại HTML/XML, chuẩn hóa whitespace, deduplicate list, kiểm tra `paper_id`, `title`, summary tối thiểu 100 ký tự và ngày hợp lệ. DOI đã chuẩn hóa được dùng làm `paper_id`. Trường ngữ nghĩa được tạo theo cấu trúc:

```text
Title: {title} | Authors: {authors_joined} | Summary: {summary}
```

Index dùng cùng embedding model cho passage và query, nhưng đúng task routing tương ứng. Ba trạng thái dùng collection và manifest riêng để tránh rò rỉ dữ liệu. Eval giữ nguyên 10 câu hỏi và ground-truth `paper_id` cho cả ba lần chạy; retrieval hit, token F1 và NVIDIA judge được lưu vào JSON. UI chỉ đọc các JSON này, còn chatbot gọi backend để API key không xuất hiện ở trình duyệt.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Crossref response; `PaperRecord`; câu hỏi eval; cấu hình provider từ environment |
| Output | Raw/clean JSON và CSV, embedding manifests, Chroma collections, eval answers/metrics, dashboard |
| Module phụ thuộc | `core.config`, `core.utils`, Jina API, ChromaDB, NVIDIA LLM provider |
| Module sử dụng output | Evaluation, dashboard API và UI; các module downstream đọc lại clean/index artifacts |
| Điều kiện lỗi cần xử lý | HTTP rate limit/5xx, thiếu title/DOI, summary ngắn, ngày không parse được, duplicate DOI, thiếu API credential, model trả về rỗng |

### Cách xác minh

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm --prefix ui run check
Invoke-RestMethod http://127.0.0.1:8001/api/health
```

- **Kết quả mong đợi:** Test Python và JavaScript đạt; backend báo đủ ba data state; artifact khớp contract.
- **Kết quả thực tế:** 9 test Python đạt; JavaScript syntax check đạt; baseline, corrupted và repaired index đều sẵn sàng.
- **Artifact/log:** `data/raw/source_manifest.json`, `data/clean/cleaning_summary.json`, `data/embeddings/papers_embeddings.json`, `data/results/*.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Embedding chỉ từ summary sẽ thiếu tín hiệu về tên bài và tác giả, trong khi nối toàn bộ metadata không cấu trúc làm nội dung khó kiểm soát.
- **Các phương án đã cân nhắc:** Chỉ embedding summary; nối mọi trường thành một chuỗi; hoặc tạo structured text từ ba trường có ý nghĩa truy xuất cao.
- **Phương án đã chọn:** Dùng `Title: ... | Authors: ... | Summary: ...` làm `text_for_embedding`.
- **Lý do:** Cấu trúc này giữ đủ tín hiệu cho truy vấn theo chủ đề, tiêu đề và tác giả, đồng thời ổn định để quality check có thể tái tạo và so sánh chính xác.
- **Bằng chứng quyết định phù hợp:** Baseline đạt `retrieval_hit_rate = 1.0` trên 10 câu thuộc bốn loại; quality check xác nhận embedding text khớp các trường nguồn.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Chatbot trả về bảng Markdown nhưng giao diện hiển thị nguyên các ký tự `| Bài báo | Chủ đề |` và `|---|---|`, làm câu trả lời khó đọc.
- **Lệnh hoặc bước tái hiện:** Mở `http://127.0.0.1:8000/ui/?chat=open` và hỏi chatbot tổng hợp nhiều bài báo dưới dạng bảng.
- **Nguyên nhân gốc:** Markdown renderer tự viết mới chỉ hỗ trợ heading, paragraph, list, quote và code block; chưa nhận diện header/divider của table.
- **Cách xử lý:** Bổ sung parser table trong `ui/app.js`, escape nội dung từng cell và render thành HTML table. Thêm CSS responsive để bảng chiếm đủ chiều rộng tin nhắn và cuộn ngang khi cần.
- **Cách xác minh sau khi sửa:** Chạy `npm --prefix ui run check`, refresh trình duyệt và kiểm tra lại cùng prompt; bảng được render đúng, không còn dòng `|---|---|` dạng text.
- **Điều học được:** Khi không dùng thư viện Markdown ngoài, renderer phải có test case cho từng cấu trúc mà LLM có thể sinh ra và luôn escape HTML trước khi render.

## 7. Hiểu biết về luồng end-to-end

1. Crossref response được lưu nguyên bản, parse thành 24 `PaperRecord`, làm sạch thành DataFrame 16 trường, tạo `text_for_embedding`, gọi Jina để sinh vector 1024 chiều rồi lưu vào Chroma.
2. Mỗi câu eval có ground-truth answer và ground-truth `paper_id`. Retrieval hit kiểm tra ID đúng có nằm trong top-k; token F1 so sánh câu trả lời; judge đánh giá correctness. Answers và metrics được lưu riêng để audit.
3. Quality checks kiểm tra completeness, uniqueness, validity và consistency tại cấp dữ liệu. Freshness tập trung vào tuổi dữ liệu, ngày mới/cũ nhất và số dòng vượt ngưỡng 180 ngày.
4. Cùng test set giúp cô lập biến độc lập là trạng thái dữ liệu. Nếu thay câu hỏi giữa ba lần chạy thì không thể quy mức giảm metric cho corruption.
5. Repair thành công khi `repair_log` cho thấy chỉ phạm vi lỗi được sửa, quality trở về 11/11, stale rows về 0 và bốn metric agent trở lại baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.8000 | 1.0000 | Corruption làm mất 2/10 retrieval hit; repair phục hồi hoàn toàn |
| `mean_token_f1` | 1.0000 | 0.8327 | 1.0000 | Nội dung lỗi làm answer overlap giảm 0.1673 |
| `judge_accuracy` | 1.0000 | 0.8000 | 1.0000 | Accuracy giảm 20 điểm phần trăm rồi phục hồi |
| `mean_judge_score` | 5.00 | 4.30 | 5.00 | Giảm 0.70 điểm trên thang 5 |
| Quality checks | 11/11 | 7/11 | 11/11 | Bốn cổng phát hiện uniqueness, summary, title và noise |
| Freshness status | Fresh, 0 stale | Stale, 2/24 | Fresh, 0 stale | Hai ngày bị lùi 365 ngày làm stale ratio thành 8.33% |

### Kết luận từ số liệu

1. Drop latest, blank summary, noise, truncate, age và duplicate → quality giảm từ 11/11 xuống 7/11, freshness có 2 dòng stale → retrieval hit và judge accuracy cùng giảm từ 1.0 xuống 0.8, mean token F1 còn 0.8327.
2. Dữ liệu repaired được cung cấp lại cho cùng retrieval/eval pipeline → quality và freshness trở lại trạng thái đạt → toàn bộ agent metrics quay về baseline.

Corruption có bằng chứng trực tiếp rõ nhất là `drop_latest_records`, vì SafeRAG là ground-truth document của một câu eval nhưng bị loại khỏi corrupted index. Blank summary và noise cũng tác động trực tiếp đến embedding text. Tuy nhiên, thí nghiệm hiện áp dụng sáu corruption cùng lúc nên chưa thể phân rã chính xác bao nhiêu metric delta thuộc riêng từng loại; muốn kết luận định lượng cần chạy ablation từng corruption.

Điểm khác kỳ vọng là corrupted dataset vẫn có 24 dòng, tưởng như row count không đổi. Corruption đã xóa 2 dòng nhưng đồng thời nhân bản 2 dòng, vì vậy chỉ còn 22 `paper_id` duy nhất. Điều này cho thấy chỉ quan sát row count sẽ bỏ sót lỗi; uniqueness và corruption log mới phát hiện đúng vấn đề.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw snapshot, stable `paper_id` và data contract là điều kiện để ingestion, cleaning và retrieval có thể tái lập.
2. Structured `text_for_embedding` giúp giữ tín hiệu tiêu đề, tác giả và nội dung trong cùng một vector nhưng vẫn có thể kiểm tra tính nhất quán.
3. UI demo phải đọc artifact thật và xử lý đầy đủ định dạng LLM có thể trả về; nếu không, kết quả kỹ thuật đúng vẫn khó trình bày và kiểm chứng.

### Nếu có thêm thời gian

Tôi sẽ mở rộng evaluation set bằng các câu hỏi tiếng Việt dạng paraphrase và multi-document synthesis, sau đó đo retrieval hit, answer correctness, latency và chi phí theo từng embedding/LLM provider. Việc này kiểm tra được khả năng tổng quát hóa tốt hơn so với 10 câu deterministic hiện tại.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Chí Hiếu

**Ngày xác nhận:** 2026-08-06
