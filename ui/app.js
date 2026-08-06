const DATA_ROOT = "../data";
const CHAT_API = "http://127.0.0.1:8001";
const PAGE_VIEW = new URLSearchParams(window.location.search).get("view") === "presentation"
  ? "presentation"
  : "dashboard";

document.body.classList.toggle("presentation-mode", PAGE_VIEW === "presentation");
const activeHash = window.location.hash || "#overview";
document.querySelectorAll("[data-nav-view]").forEach((link) => {
  const isActive = PAGE_VIEW === "presentation"
    ? link.dataset.navView === "presentation"
    : link.dataset.navView === "dashboard" && link.getAttribute("href").endsWith(activeHash);
  link.classList.toggle("active", isActive);
});

const artifactPaths = {
  metrics: {
    baseline: `${DATA_ROOT}/results/baseline_metrics.json`,
    corrupted: `${DATA_ROOT}/results/corrupted_metrics.json`,
    repaired: `${DATA_ROOT}/results/repaired_metrics.json`,
  },
  answers: {
    baseline: `${DATA_ROOT}/results/baseline_answers.json`,
    corrupted: `${DATA_ROOT}/results/corrupted_answers.json`,
    repaired: `${DATA_ROOT}/results/repaired_answers.json`,
  },
  quality: {
    baseline: `${DATA_ROOT}/quality/baseline.json`,
    corrupted: `${DATA_ROOT}/quality/corrupted.json`,
    repaired: `${DATA_ROOT}/quality/repaired.json`,
  },
  freshness: {
    baseline: `${DATA_ROOT}/quality/freshness_report.json`,
    corrupted: `${DATA_ROOT}/quality/freshness_corrupted.json`,
    repaired: `${DATA_ROOT}/quality/freshness_repaired.json`,
  },
  corruptionLog: `${DATA_ROOT}/results/corruption_log.json`,
  repairLog: `${DATA_ROOT}/results/repair_log.json`,
  papers: `${DATA_ROOT}/clean/papers_clean.json`,
  manifest: `${DATA_ROOT}/embeddings/papers_embeddings.json`,
};

const stateLabels = {
  baseline: "Dữ liệu gốc",
  corrupted: "Dữ liệu lỗi",
  repaired: "Dữ liệu đã sửa",
};

const chatStateDescriptions = {
  baseline: "Truy vấn index dữ liệu sạch trước khi gây lỗi.",
  corrupted: "Truy vấn index chứa corruption để quan sát mức suy giảm.",
  repaired: "Truy vấn index sau khi sửa có mục tiêu từ dữ liệu tốt.",
};

const questionTypeLabels = {
  summary: "tóm tắt",
  authors: "tác giả",
  date: "ngày xuất bản",
  categories: "danh mục",
};

const corruptionLabels = {
  drop_latest_records: ["Loại bản ghi mới nhất", "Loại hai bản ghi mới nhất để mô phỏng mất độ tươi mới."],
  blank_summary: ["Xóa nội dung tóm tắt", "Đặt summary thành rỗng trên hai dòng để phá completeness."],
  inject_noise: ["Chèn token nhiễu", "Chèn token nhiễu vào text_for_embedding trên hai dòng."],
  truncate_title: ["Cắt ngắn tiêu đề", "Cắt title còn khoảng một phần ba độ dài trên hai dòng."],
  age_published_dates: ["Làm cũ ngày xuất bản", "Lùi ngày xuất bản 365 ngày trên hai dòng."],
  duplicate_rows: ["Nhân bản dòng", "Nhân bản hai dòng để phá tính duy nhất của paper_id."],
};

const corruptionImpactLabels = {
  drop_latest_records: {
    dataset: "Thiếu 2 bản ghi mới nhất; độ phủ giảm từ 24 xuống 22 paper_id duy nhất.",
    rag: "Mất tài liệu liên quan khỏi top-k và làm giảm độ tươi mới.",
  },
  blank_summary: {
    dataset: "2 summary rỗng; summary_chars và nội dung embedding mất tính đầy đủ.",
    rag: "Vector mất ngữ nghĩa của phần tóm tắt nên truy xuất kém chính xác hơn.",
  },
  inject_noise: {
    dataset: "2 text_for_embedding không còn khớp với các trường nguồn.",
    rag: "Vector bị lệch và thứ hạng cosine của tài liệu có thể giảm.",
  },
  truncate_title: {
    dataset: "2 tiêu đề chỉ còn khoảng một phần ba nội dung.",
    rag: "Truy vấn theo tiêu đề và trích dẫn nguồn trở nên kém tin cậy.",
  },
  age_published_dates: {
    dataset: "2 ngày xuất bản bị lùi 365 ngày và age_days tăng sai.",
    rag: "Báo cáo freshness thất bại; tài liệu mới bị xem như đã cũ.",
  },
  duplicate_rows: {
    dataset: "Thêm 2 dòng trùng, khiến 24 dòng chỉ còn 22 paper_id duy nhất.",
    rag: "Vector trùng có thể chiếm chỗ của bằng chứng khác trong top-k.",
  },
};

const qualityCheckLabels = {
  row_count: "Số lượng dòng",
  paper_id_not_null: "paper_id không null",
  paper_id_unique: "paper_id duy nhất",
  title_not_blank: "Title không rỗng",
  title_not_truncated: "Title không bị cắt",
  summary_min_length: "Summary đủ độ dài",
  summary_chars_matches_summary: "summary_chars khớp summary",
  age_days_non_negative: "age_days không âm",
  text_for_embedding_not_empty: "Embedding text không rỗng",
  text_for_embedding_matches_source_fields: "Embedding text khớp trường nguồn",
  text_for_embedding_has_no_noise_tokens: "Embedding text không có token nhiễu",
};

const translateQualityText = (value) => String(value)
  .replaceAll("noisy row(s)", "dòng có nhiễu")
  .replaceAll("noisy rows", "dòng có nhiễu")
  .replaceAll("rows", "dòng")
  .replaceAll("row(s)", "dòng")
  .replaceAll("null(s)", "giá trị null")
  .replaceAll("nulls", "giá trị null")
  .replaceAll("duplicate(s)", "bản ghi trùng")
  .replaceAll("duplicates", "bản ghi trùng")
  .replaceAll("blank(s)", "giá trị rỗng")
  .replaceAll("blanks", "giá trị rỗng")
  .replaceAll("truncated title(s)", "title bị cắt")
  .replaceAll("truncated titles", "title bị cắt")
  .replaceAll("mismatch(es)", "giá trị không khớp")
  .replaceAll("mismatches", "giá trị không khớp")
  .replaceAll("empty(s)", "giá trị rỗng")
  .replaceAll("empty", "rỗng");

const fetchJson = async (path) => {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${path} trả về mã HTTP ${response.status}`);
  return response.json();
};

const loadArtifacts = async () => {
  const entries = [];
  for (const group of ["metrics", "answers", "quality", "freshness"]) {
    for (const [state, path] of Object.entries(artifactPaths[group])) {
      entries.push([`${group}.${state}`, path]);
    }
  }
  entries.push(["corruptionLog", artifactPaths.corruptionLog]);
  entries.push(["repairLog", artifactPaths.repairLog]);
  entries.push(["papers", artifactPaths.papers]);
  entries.push(["manifest", artifactPaths.manifest]);

  const values = await Promise.all(entries.map(([, path]) => fetchJson(path)));
  const data = { metrics: {}, answers: {}, quality: {}, freshness: {} };
  entries.forEach(([key], index) => {
    const [group, state] = key.split(".");
    if (state) data[group][state] = values[index];
    else data[group] = values[index];
  });
  return data;
};

const percent = (value, digits = 0) => `${(Number(value) * 100).toFixed(digits)}%`;
const escapeHtml = (value = "") => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

const renderInlineMarkdown = (value) => escapeHtml(value)
  .replace(/`([^`]+)`/g, "<code>$1</code>")
  .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
  .replace(/__([^_]+)__/g, "<strong>$1</strong>")
  .replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, "<em>$1</em>")
  .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');

const parseMarkdownTableRow = (line) => line
  .trim()
  .replace(/^\|/, "")
  .replace(/\|$/, "")
  .split(/(?<!\\)\|/)
  .map((cell) => cell.trim().replaceAll("\\|", "|"));

const isMarkdownTableDivider = (line = "") => {
  if (!line.includes("|")) return false;
  const cells = parseMarkdownTableRow(line);
  return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
};

const renderMarkdown = (markdown = "") => {
  const lines = String(markdown).replaceAll("\r\n", "\n").split("\n");
  const output = [];
  let paragraph = [];
  let listType = "";
  let listItems = [];
  let codeLines = [];
  let inCodeBlock = false;

  const flushParagraph = () => {
    if (!paragraph.length) return;
    output.push(`<p>${paragraph.map(renderInlineMarkdown).join("<br>")}</p>`);
    paragraph = [];
  };
  const flushList = () => {
    if (!listItems.length) return;
    output.push(`<${listType}>${listItems.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join("")}</${listType}>`);
    listType = "";
    listItems = [];
  };

  for (let lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
    const line = lines[lineIndex];
    if (line.trim().startsWith("```")) {
      flushParagraph();
      flushList();
      if (inCodeBlock) {
        output.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
        codeLines = [];
      }
      inCodeBlock = !inCodeBlock;
      continue;
    }
    if (inCodeBlock) {
      codeLines.push(line);
      continue;
    }

    if (line.includes("|") && isMarkdownTableDivider(lines[lineIndex + 1])) {
      flushParagraph();
      flushList();
      const headers = parseMarkdownTableRow(line);
      const rows = [];
      lineIndex += 2;
      while (lineIndex < lines.length && lines[lineIndex].trim() && lines[lineIndex].includes("|")) {
        rows.push(parseMarkdownTableRow(lines[lineIndex]));
        lineIndex += 1;
      }
      lineIndex -= 1;
      const columnCount = headers.length;
      output.push(`<div class="markdown-table-wrap"><table><thead><tr>${headers.map((cell) => `<th>${renderInlineMarkdown(cell)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${Array.from({ length: columnCount }, (_, index) => `<td>${renderInlineMarkdown(row[index] || "")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    const unordered = line.match(/^\s*[-*+]\s+(.+)$/);
    const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
    const quote = line.match(/^>\s?(.*)$/);
    if (heading) {
      flushParagraph();
      flushList();
      const level = heading[1].length;
      output.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
    } else if (unordered || ordered) {
      flushParagraph();
      const nextType = unordered ? "ul" : "ol";
      if (listType && listType !== nextType) flushList();
      listType = nextType;
      listItems.push((unordered || ordered)[1]);
    } else if (quote) {
      flushParagraph();
      flushList();
      output.push(`<blockquote>${renderInlineMarkdown(quote[1])}</blockquote>`);
    } else if (!line.trim()) {
      flushParagraph();
      flushList();
    } else {
      flushList();
      paragraph.push(line);
    }
  }
  flushParagraph();
  flushList();
  if (codeLines.length) output.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
  return output.join("");
};

const renderKpis = (data) => {
  const baselineQuality = data.quality.baseline.summary;
  const corruptedQuality = data.quality.corrupted.summary;
  const repaired = data.metrics.repaired;
  const baseline = data.metrics.baseline;
  const recoveryMetrics = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy"];
  const recovered = recoveryMetrics.filter((key) => repaired[key] >= baseline[key]).length;
  const repairRate = recovered / recoveryMetrics.length;

  document.querySelector("#total-records").textContent = data.papers.length.toLocaleString();
  document.querySelector("#record-meta").textContent = `${data.manifest.documents.length} vector · ${data.manifest.embedding_dimension} chiều`;
  const qualityRate = baselineQuality.passed / baselineQuality.total_checks;
  document.querySelector("#quality-rate").textContent = percent(qualityRate);
  document.querySelector("#quality-meter").style.width = percent(qualityRate);
  document.querySelector("#corruption-signals").textContent = corruptedQuality.failed;
  document.querySelector("#corruption-meta").textContent = `${data.corruptionLog.entries.length} kịch bản · ${corruptedQuality.total_checks} cổng kiểm tra`;
  document.querySelector("#repair-rate").textContent = percent(repairRate);
  document.querySelector("#repair-meta").textContent = `${data.quality.repaired.summary.passed}/${data.quality.repaired.summary.total_checks} cổng chất lượng đạt`;
};

const renderQuestion = (data, index) => {
  const baseline = data.answers.baseline[index];
  if (!baseline) return;
  document.querySelector("#selected-question").textContent = baseline.question;
  document.querySelector("#question-index").textContent = `${String(index + 1).padStart(2, "0")} / ${String(data.answers.baseline.length).padStart(2, "0")}`;

  document.querySelector("#state-grid").innerHTML = ["baseline", "corrupted", "repaired"].map((state) => {
    const item = data.answers[state][index];
    const score = item.judge?.score ?? 0;
    return `
      <article class="state-card ${state}">
        <div class="state-header">
          <span class="state-name"><i class="state-dot"></i>${stateLabels[state]}</span>
          <span class="status-chip ${item.retrieval_hit ? "success" : "danger"}">${item.retrieval_hit ? "Trúng" : "Trượt"}</span>
        </div>
        <p class="state-answer">${escapeHtml(item.answer)}</p>
        <div class="state-footer">
          <div class="retrieval-line">${item.retrieved_doc_ids.length} bài báo · ${escapeHtml(item.retrieved_doc_ids[0] || "Không có kết quả")}</div>
          <div class="mini-metrics">
            <div class="mini-metric"><span>Token F1</span><strong>${item.token_f1.toFixed(2)}</strong></div>
            <div class="mini-metric"><span>Giám khảo</span><strong>${score}/5</strong></div>
            <div class="mini-metric"><span>Nền tảng</span><strong>${escapeHtml(item.judge_backend.replace("llm:", ""))}</strong></div>
          </div>
        </div>
      </article>`;
  }).join("");
};

const setupQuestions = (data) => {
  const select = document.querySelector("#question-select");
  select.innerHTML = data.answers.baseline.map((item, index) =>
    `<option value="${index}">${escapeHtml(item.id)} · ${escapeHtml(questionTypeLabels[item.question_type] || item.question_type)}</option>`
  ).join("");
  select.addEventListener("change", () => renderQuestion(data, Number(select.value)));

  const search = document.querySelector("#global-search");
  search.addEventListener("input", () => {
    const needle = search.value.trim().toLowerCase();
    if (!needle) return;
    const index = data.answers.baseline.findIndex((item) =>
      item.question.toLowerCase().includes(needle) || item.question_type.toLowerCase().includes(needle)
    );
    if (index >= 0) {
      select.value = String(index);
      renderQuestion(data, index);
      document.querySelector("#evaluations").scrollIntoView({ behavior: "smooth" });
    }
  });
  renderQuestion(data, 0);
};

const renderMetrics = (data) => {
  const metrics = [
    ["Tỷ lệ retrieval trúng", "retrieval_hit_rate"],
    ["Token F1", "mean_token_f1"],
    ["Độ chính xác giám khảo", "judge_accuracy"],
    ["Điểm giám khảo", "mean_judge_score", 5],
  ];
  document.querySelector("#metric-comparison").innerHTML = metrics.map(([label, key, maximum = 1]) => {
    const rows = ["baseline", "corrupted", "repaired"].map((state) => {
      const value = data.metrics[state][key];
      return `<div class="metric-bar ${state}" title="${stateLabels[state]}: ${value.toFixed(3)}"><span style="width:${(value / maximum) * 100}%"></span></div>`;
    }).join("");
    const repairedValue = data.metrics.repaired[key];
    return `<div class="metric-row"><span class="metric-label">${label}</span><div class="bar-stack">${rows}</div><span class="metric-value">${key === "mean_judge_score" ? repairedValue.toFixed(1) : percent(repairedValue)}</span></div>`;
  }).join("") + `
    <div class="bar-legend">
      <span><i style="background:var(--success)"></i>Gốc</span>
      <span><i style="background:var(--danger)"></i>Bị lỗi</span>
      <span><i style="background:var(--repair)"></i>Đã sửa</span>
    </div>`;
};

const renderFreshness = (data) => {
  const current = data.freshness.repaired;
  const corrupted = data.freshness.corrupted;
  const status = document.querySelector("#freshness-status");
  status.textContent = current.is_fresh ? "Tốt" : "Quá hạn";
  status.classList.add(current.is_fresh ? "success" : "danger");
  document.querySelector("#freshness-age").textContent = current.threshold_days;
  document.querySelector("#freshness-details").innerHTML = `
    <div><dt>Bài mới nhất</dt><dd>${escapeHtml(current.latest_published)}</dd></div>
    <div><dt>Bài cũ nhất</dt><dd>${escapeHtml(current.oldest_published)}</dd></div>
    <div><dt>Dòng quá hạn trong dữ liệu lỗi</dt><dd>${corrupted.stale_rows}</dd></div>
    <div><dt>Dòng quá hạn sau khi sửa</dt><dd>${current.stale_rows}</dd></div>`;
  document.querySelector("#artifact-time").textContent = `Ảnh chụp · ${new Date(current.generated_at_utc).toLocaleString("vi-VN")}`;
};

const renderQuality = (data, state) => {
  const report = data.quality[state];
  document.querySelector("#quality-summary").innerHTML = `
    <span class="quality-score">${report.summary.passed}/${report.summary.total_checks}</span>
    <span>${stateLabels[state]}: kiểm tra đạt · ${report.summary.failed} lỗi</span>`;
  document.querySelector("#quality-table").innerHTML = report.checks.map((check) => `
    <tr>
      <td>${escapeHtml(qualityCheckLabels[check.check] || check.check)}</td>
      <td>${escapeHtml({ Completeness: "Đầy đủ", Uniqueness: "Duy nhất", Validity: "Hợp lệ", Consistency: "Nhất quán" }[check.quality_dimension] || check.quality_dimension)}</td>
      <td>${escapeHtml(translateQualityText(check.observed))}</td>
      <td>${escapeHtml(translateQualityText(check.expected))}</td>
      <td><span class="check-status ${check.passed ? "pass" : "fail"}">${check.passed ? "ĐẠT" : "LỖI"}</span></td>
    </tr>`).join("");
};

const setupQualityTabs = (data) => {
  document.querySelector("#quality-tabs").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-state]");
    if (!button) return;
    document.querySelectorAll("#quality-tabs button").forEach((item) => item.classList.toggle("active", item === button));
    renderQuality(data, button.dataset.state);
  });
  renderQuality(data, "baseline");
};

const renderCorruptionLog = (data) => {
  document.querySelector("#corruption-count").textContent = `${data.corruptionLog.entries.length} kịch bản`;
  document.querySelector("#corruption-timeline").innerHTML = data.corruptionLog.entries.map((entry) => `
    <div class="timeline-item">
      <div class="timeline-title"><span>${escapeHtml(corruptionLabels[entry.corruption]?.[0] || entry.corruption)}</span><span>×${entry.count}</span></div>
      <p class="timeline-description">${escapeHtml(corruptionLabels[entry.corruption]?.[1] || entry.description)}</p>
    </div>`).join("");
};

const renderPapers = (data) => {
  document.querySelector("#paper-list").innerHTML = data.papers.slice(0, 5).map((paper) => `
    <div class="paper-item">
      <a href="${escapeHtml(paper.abs_url)}" target="_blank" rel="noreferrer">${escapeHtml(paper.title)}</a>
      <div class="paper-meta">${escapeHtml(paper.paper_id)} · ${escapeHtml(paper.published)} · ${escapeHtml(paper.primary_category)}</div>
    </div>`).join("");
};

const setupPresentation = (data) => {
  const questionTypes = data.answers.baseline.reduce((counts, item) => {
    counts[item.question_type] = (counts[item.question_type] || 0) + 1;
    return counts;
  }, {});
  const metricValue = (state, key, asScore = false) => asScore
    ? data.metrics[state][key].toFixed(1)
    : percent(data.metrics[state][key], 1);
  const corruptionCards = data.corruptionLog.entries.map((entry) => `
    <div class="slide-card">
      <span class="slide-number">×${entry.count}</span>
      <strong>${escapeHtml(corruptionLabels[entry.corruption]?.[0] || entry.corruption.replaceAll("_", " "))}</strong>
      <p class="impact-line"><b>Dataset</b>${escapeHtml(corruptionImpactLabels[entry.corruption]?.dataset || entry.dataset_impact)}</p>
      <p class="impact-line rag"><b>RAG</b>${escapeHtml(corruptionImpactLabels[entry.corruption]?.rag || entry.rag_impact)}</p>
    </div>`).join("");

  const slides = [
    {
      kicker: "Ngày 10 · Data pipeline và observability",
      title: "Từ dữ liệu khoa học thô đến hệ thống RAG có thể quan sát",
      lead: "Một pipeline có thể tái lập để thu thập, làm sạch, embedding, đánh giá, gây lỗi, sửa chữa và chứng minh chất lượng retrieval bằng bằng chứng.",
      body: `<div class="slide-grid">
        <div class="slide-card"><span class="slide-number">${data.papers.length}</span><strong>Bài báo sạch</strong><p>Các bản ghi Crossref còn lại sau data contract bắt buộc.</p></div>
        <div class="slide-card"><span class="slide-number">${percent(data.metrics.baseline.retrieval_hit_rate)}</span><strong>Tỷ lệ truy xuất trúng ban đầu</strong><p>Đo trên cùng bộ đánh giá đa dạng gồm 10 câu hỏi.</p></div>
        <div class="slide-card"><span class="slide-number">${data.quality.repaired.summary.passed}/${data.quality.repaired.summary.total_checks}</span><strong>Cổng đã phục hồi</strong><p>Mọi kiểm tra chất lượng đều đạt lại sau quá trình sửa xác định.</p></div>
      </div>`,
      note: "Mở đầu bằng kết quả: nhóm đã xây dựng một thí nghiệm hoàn chỉnh, không chỉ là demo retrieval.",
    },
    {
      kicker: "01 · Nền tảng dữ liệu",
      title: "Thu thập Crossref và data contract làm sạch nghiêm ngặt",
      lead: "Pipeline lưu snapshot phản hồi thô, parse bản ghi rồi tạo artifact CSV và JSON ổn định cho mọi bước phía sau.",
      body: `<div class="slide-grid">
        <div class="slide-card"><span class="slide-number">01</span><strong>Lọc dòng không sử dụng được</strong><p>Yêu cầu title, ngày xuất bản hợp lệ và summary dài tối thiểu 100 ký tự.</p></div>
        <div class="slide-card"><span class="slide-number">02</span><strong>Chuẩn hóa các trường</strong><p>Loại XML/HTML, nối authors và categories, chuẩn hóa ngày, tính age_days.</p></div>
        <div class="slide-card"><span class="slide-number">03</span><strong>Tạo văn bản ngữ nghĩa</strong><p>Title + authors + summary trở thành trường text_for_embedding xác định.</p></div>
      </div>`,
      note: "Nhấn mạnh dữ liệu raw không bị chỉnh sửa; artifact clean được dẫn xuất và có thể tái lập.",
    },
    {
      kicker: "02 · Hệ thống end-to-end",
      title: "Một luồng có thể truy vết từ nguồn đến câu trả lời",
      lead: "Mỗi bước đều lưu artifact, nhờ đó lỗi có thể quan sát và phép so sánh có thể lặp lại.",
      body: `<div class="pipeline-flow">
        <div class="flow-node"><i>1</i><strong>Crossref</strong><span>24 bản ghi raw</span></div>
        <div class="flow-node"><i>2</i><strong>Làm sạch</strong><span>kiểm tra contract</span></div>
        <div class="flow-node"><i>3</i><strong>Jina</strong><span>vector 1024 chiều</span></div>
        <div class="flow-node"><i>4</i><strong>Chroma</strong><span>retrieval cosine</span></div>
        <div class="flow-node"><i>5</i><strong>NVIDIA</strong><span>trả lời có căn cứ</span></div>
        <div class="flow-node"><i>6</i><strong>Đánh giá</strong><span>metric + báo cáo</span></div>
      </div>`,
      note: "Đi từ trái sang phải và chỉ ra mỗi mũi tên đều có artifact đã commit hoặc đầu ra đo được.",
    },
    {
      kicker: "03 · Lớp retrieval",
      title: "Jina embedding với các Chroma collection độc lập",
      lead: "Cùng một mô hình embedding được dùng cho đoạn văn và truy vấn, trong khi ba trạng thái dữ liệu được cách ly.",
      body: `<div class="slide-grid">
        <div class="slide-card"><span class="slide-number">1024d</span><strong>${escapeHtml(data.manifest.embedding_model)}</strong><p>Embedding passage/query theo đúng task từ Jina.</p></div>
        <div class="slide-card"><span class="slide-number">3</span><strong>Bộ sưu tập độc lập</strong><p>Ba collection Chroma riêng biệt ngăn rò rỉ trạng thái dữ liệu.</p></div>
        <div class="slide-card"><span class="slide-number">Top 4</span><strong>Truy xuất bằng chứng</strong><p>Lưu paper, ID, title, context và score được xếp hạng cosine để đánh giá.</p></div>
      </div>`,
      note: "Nêu rõ thành viên nhóm có thể query Chroma artifact đã commit; chỉ khi rebuild mới cần Jina key.",
    },
    {
      kicker: "04 · Thiết kế đánh giá",
      title: "Mười câu hỏi kiểm thử nhiều dạng retrieval",
      lead: "Mỗi câu đều có ground-truth answer và document ID, cho phép đo cả retrieval lẫn chất lượng câu trả lời.",
      body: `<div class="slide-grid two">
        <div class="slide-card"><span class="slide-number">${data.answers.baseline.length}</span><strong>Câu hỏi đa dạng</strong><p>${Object.entries(questionTypes).map(([type, count]) => `${count} ${escapeHtml(questionTypeLabels[type] || type)}`).join(" · ")}.</p></div>
        <div class="slide-card"><span class="slide-number">4</span><strong>Tín hiệu cốt lõi</strong><p>Retrieval hit rate, token F1, độ chính xác và điểm của NVIDIA judge.</p></div>
        <div class="slide-card"><span class="slide-number">Cùng bộ</span><strong>So sánh công bằng</strong><p>Ba trạng thái dữ liệu trả lời cùng một tập câu hỏi.</p></div>
        <div class="slide-card"><span class="slide-number">Nguồn</span><strong>Câu trả lời kiểm toán được</strong><p>DOI, ngữ cảnh, điểm, nền tảng chấm và lập luận đều được lưu.</p></div>
      </div>`,
      note: "Giải thích vì sao phải dùng cùng bộ eval: chỉ trạng thái dữ liệu thay đổi.",
    },
    {
      kicker: "05 · Thí nghiệm khả năng quan sát",
      className: "impact-slide",
      title: "Corruption có kiểm soát làm suy giảm chất lượng một cách nhìn thấy được",
      lead: "Mỗi thay đổi đều ghi rõ paper_id bị tác động, ảnh hưởng lên dataset và hậu quả trực tiếp đối với retrieval.",
      body: `<div class="slide-grid">${corruptionCards}</div>`,
      note: "Không mô tả corruption là lỗi ngẫu nhiên; nó có seed và log để thí nghiệm có thể tái lập.",
    },
    {
      kicker: "06 · Quy trình phục hồi",
      title: "Chỉ sửa phần bị lỗi bằng dữ liệu tốt làm tham chiếu",
      lead: `Corruption log khoanh vùng ${data.repairLog.targeted_unique_records} paper_id cần xử lý; ${data.repairLog.unaffected_reference_records} bản ghi tốt còn lại không bị thay nội dung.`,
      body: `<div class="pipeline-flow repair-flow">
        <div class="flow-node"><i>1</i><strong>Đọc corruption log</strong><span>loại lỗi + paper_id</span></div>
        <div class="flow-node"><i>2</i><strong>Đối chiếu dữ liệu tốt</strong><span>papers_clean.csv</span></div>
        <div class="flow-node"><i>3</i><strong>Sửa đúng trường lỗi</strong><span>title / summary / date / text</span></div>
        <div class="flow-node"><i>4</i><strong>Sửa cấu trúc dòng</strong><span>+2 thiếu / −2 trùng</span></div>
        <div class="flow-node"><i>5</i><strong>Xác nhận phục hồi</strong><span>quality + freshness + eval</span></div>
      </div>
      <div class="takeaway"><strong>Kết quả có mục tiêu</strong><span>${data.repairLog.before.unique_paper_ids} → ${data.repairLog.after.unique_paper_ids} paper_id duy nhất; 11/11 cổng đạt và metric trở về mức gốc.</span></div>`,
      note: "Module repair chỉ dùng các ID trong corruption_log. Summary khôi phục 3 trường dẫn xuất; noise 1 trường; title 2 trường; date 2 trường; thêm 2 dòng thiếu và bỏ 2 bản sao trùng.",
    },
    {
      kicker: "07 · Kết quả đo lường",
      title: "Dữ liệu lỗi làm giảm truy xuất; quá trình sửa phục hồi kết quả",
      lead: "Cổng chất lượng và chỉ số câu trả lời cùng biến đổi, chứng minh khả năng quan sát dữ liệu ảnh hưởng trực tiếp đến hành vi RAG.",
      body: `<table class="slide-metric-table">
        <thead><tr><th>Tín hiệu</th><th>Dữ liệu gốc</th><th>Dữ liệu lỗi</th><th>Đã sửa</th></tr></thead>
        <tbody>
          <tr><td>Tỷ lệ retrieval trúng</td><td>${metricValue("baseline", "retrieval_hit_rate")}</td><td class="result-down">${metricValue("corrupted", "retrieval_hit_rate")}</td><td class="result-up">${metricValue("repaired", "retrieval_hit_rate")}</td></tr>
          <tr><td>Token F1 trung bình</td><td>${metricValue("baseline", "mean_token_f1")}</td><td class="result-down">${metricValue("corrupted", "mean_token_f1")}</td><td class="result-up">${metricValue("repaired", "mean_token_f1")}</td></tr>
          <tr><td>Độ chính xác judge</td><td>${metricValue("baseline", "judge_accuracy")}</td><td class="result-down">${metricValue("corrupted", "judge_accuracy")}</td><td class="result-up">${metricValue("repaired", "judge_accuracy")}</td></tr>
          <tr><td>Điểm judge trung bình</td><td>${metricValue("baseline", "mean_judge_score", true)}/5</td><td class="result-down">${metricValue("corrupted", "mean_judge_score", true)}/5</td><td class="result-up">${metricValue("repaired", "mean_judge_score", true)}/5</td></tr>
          <tr><td>Cổng chất lượng đạt</td><td>${data.quality.baseline.summary.passed}/${data.quality.baseline.summary.total_checks}</td><td class="result-down">${data.quality.corrupted.summary.passed}/${data.quality.corrupted.summary.total_checks}</td><td class="result-up">${data.quality.repaired.summary.passed}/${data.quality.repaired.summary.total_checks}</td></tr>
        </tbody>
      </table>
      <div class="takeaway"><strong>Kết luận chính</strong><span>Quá trình sửa đưa toàn bộ chỉ số cốt lõi và 11 cổng chất lượng trở lại mức ban đầu.</span></div>`,
      note: "Dừng ở cột dữ liệu lỗi: tỷ lệ truy xuất trúng giảm còn 80% và bốn cổng chất lượng lỗi, sau đó đều phục hồi.",
    },
    {
      kicker: "08 · Demo và kết luận",
      title: "Dashboard biến artifact thành câu chuyện sẵn sàng để nhóm trình bày",
      lead: "Demo kết hợp bằng chứng thí nghiệm với chatbot RAG trực tiếp mà không đưa API key ra trình duyệt.",
      body: `<div class="slide-grid">
        <div class="slide-card"><span class="slide-number">Quan sát</span><strong>So sánh trạng thái</strong><p>Khám phá KPI, câu trả lời từng câu, freshness, quality gate và corruption log.</p></div>
        <div class="slide-card"><span class="slide-number">Hỏi</span><strong>Chat với kho dữ liệu</strong><p>Jina query → bằng chứng Chroma → NVIDIA trả lời kèm DOI và score.</p></div>
        <div class="slide-card"><span class="slide-number">Cải tiến</span><strong>Vòng lặp tiếp theo</strong><p>Thêm Ragas, nguồn dữ liệu mới, telemetry latency/chi phí và giám sát liên tục.</p></div>
      </div>
      <div class="takeaway"><strong>Kết luận</strong><span>RAG đáng tin cậy cần chất lượng dữ liệu đo được, đánh giá tái lập và câu trả lời có bằng chứng.</span></div>`,
      note: "Kết thúc bằng cách mở Hỏi kho dữ liệu, chạy một câu trực tiếp rồi mời lớp đặt câu hỏi.",
    },
  ];

  const container = document.querySelector("#presentation-slides");
  const dots = document.querySelector("#slide-dots");
  const currentLabel = document.querySelector("#slide-current");
  const totalLabel = document.querySelector("#slide-total");
  const progress = document.querySelector("#deck-progress-bar");
  const note = document.querySelector("#speaker-note");
  const deck = document.querySelector("#slide-deck");
  const prev = document.querySelector("#slide-prev");
  const next = document.querySelector("#slide-next");
  let current = 0;

  container.innerHTML = slides.map((slide, index) => `
    <article class="presentation-slide ${slide.className || ""} ${index === 0 ? "active" : ""}" data-slide="${index}">
      <p class="slide-kicker">${slide.kicker}</p>
      <h3>${slide.title}</h3>
      <p class="slide-lead">${slide.lead}</p>
      ${slide.body}
    </article>`).join("");
  dots.innerHTML = slides.map((_, index) => `<button class="slide-dot ${index === 0 ? "active" : ""}" data-slide-target="${index}" aria-label="Đi đến trang trình chiếu ${index + 1}"></button>`).join("");
  totalLabel.textContent = String(slides.length).padStart(2, "0");

  const showSlide = (index) => {
    current = Math.max(0, Math.min(index, slides.length - 1));
    container.querySelectorAll(".presentation-slide").forEach((element, slideIndex) => element.classList.toggle("active", slideIndex === current));
    dots.querySelectorAll(".slide-dot").forEach((element, slideIndex) => element.classList.toggle("active", slideIndex === current));
    currentLabel.textContent = String(current + 1).padStart(2, "0");
    progress.style.width = `${((current + 1) / slides.length) * 100}%`;
    note.textContent = slides[current].note;
    prev.disabled = current === 0;
    next.disabled = current === slides.length - 1;
  };

  prev.addEventListener("click", () => showSlide(current - 1));
  next.addEventListener("click", () => showSlide(current + 1));
  dots.addEventListener("click", (event) => {
    const target = event.target.closest("[data-slide-target]");
    if (target) showSlide(Number(target.dataset.slideTarget));
  });
  document.querySelector("#presentation-fullscreen").addEventListener("click", async () => {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await deck.requestFullscreen();
  });
  document.addEventListener("keydown", (event) => {
    const visible = document.fullscreenElement === deck || document.querySelector("#presentation").getBoundingClientRect().top < window.innerHeight;
    if (!visible || ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) return;
    if (event.key === "ArrowRight" || event.key === "PageDown") showSlide(current + 1);
    if (event.key === "ArrowLeft" || event.key === "PageUp") showSlide(current - 1);
  });
  const requestedSlide = Number(new URLSearchParams(window.location.search).get("slide"));
  showSlide(Number.isInteger(requestedSlide) && requestedSlide > 0 ? requestedSlide - 1 : 0);

};

const setupTheme = () => {
  document.querySelector("#theme-toggle").addEventListener("click", () => {
    document.documentElement.classList.toggle("dark");
  });
};

const setupChat = () => {
  const drawer = document.querySelector("#chat-drawer");
  const backdrop = document.querySelector("#chat-backdrop");
  const launcher = document.querySelector("#chat-launcher");
  const close = document.querySelector("#chat-close");
  const resizeHandle = document.querySelector("#chat-resize-handle");
  const form = document.querySelector("#chat-form");
  const input = document.querySelector("#chat-input");
  const submit = document.querySelector("#chat-submit");
  const messages = document.querySelector("#chat-messages");
  const status = document.querySelector("#chat-status-text");
  const statusRow = status.parentElement;
  const stateSelector = document.querySelector("#chat-state-selector");
  const stateDescription = document.querySelector("#chat-state-description");
  const history = [];
  let chatDataState = "baseline";
  const minimumWidth = 340;
  const defaultWidth = 460;

  const applyChatWidth = (width) => {
    const maximumWidth = Math.min(860, window.innerWidth - 24);
    const safeWidth = Math.max(minimumWidth, Math.min(width, maximumWidth));
    drawer.style.setProperty("--chat-width", `${safeWidth}px`);
    return safeWidth;
  };

  const storedWidth = Number(localStorage.getItem("qualitrace-chat-width"));
  if (Number.isFinite(storedWidth) && storedWidth > 0) applyChatWidth(storedWidth);

  resizeHandle.addEventListener("pointerdown", (event) => {
    if (window.matchMedia("(max-width: 680px)").matches) return;
    event.preventDefault();
    resizeHandle.setPointerCapture(event.pointerId);
    document.body.classList.add("chat-resizing");
  });
  resizeHandle.addEventListener("pointermove", (event) => {
    if (!resizeHandle.hasPointerCapture(event.pointerId)) return;
    applyChatWidth(window.innerWidth - event.clientX);
  });
  const finishResize = (event) => {
    if (!resizeHandle.hasPointerCapture(event.pointerId)) return;
    resizeHandle.releasePointerCapture(event.pointerId);
    document.body.classList.remove("chat-resizing");
    localStorage.setItem("qualitrace-chat-width", String(Math.round(drawer.getBoundingClientRect().width)));
  };
  resizeHandle.addEventListener("pointerup", finishResize);
  resizeHandle.addEventListener("pointercancel", finishResize);
  resizeHandle.addEventListener("dblclick", () => {
    applyChatWidth(defaultWidth);
    localStorage.removeItem("qualitrace-chat-width");
  });
  window.addEventListener("resize", () => {
    if (!window.matchMedia("(max-width: 680px)").matches) {
      applyChatWidth(drawer.getBoundingClientRect().width || defaultWidth);
    }
  });

  const setOpen = (open) => {
    drawer.classList.toggle("open", open);
    backdrop.classList.toggle("open", open);
    drawer.setAttribute("aria-hidden", String(!open));
    launcher.setAttribute("aria-expanded", String(open));
    if (open) setTimeout(() => input.focus(), 180);
  };
  launcher.addEventListener("click", () => setOpen(true));
  close.addEventListener("click", () => setOpen(false));
  backdrop.addEventListener("click", () => setOpen(false));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setOpen(false);
  });
  if (new URLSearchParams(window.location.search).get("chat") === "open") {
    setOpen(true);
  }

  const addMessage = (role, content, sources = [], mode = "") => {
    const article = document.createElement("article");
    article.className = `chat-message ${role}`;
    const sourceHtml = sources.length ? `<div class="chat-sources">${sources.slice(0, 3).map((source, index) => `
      <a class="chat-source" href="${escapeHtml(source.url || "#")}" target="_blank" rel="noreferrer">
        <strong>[Nguồn ${index + 1}] ${escapeHtml(source.title)}</strong>
        <span>${escapeHtml(source.paper_id)} · điểm ${Number(source.score).toFixed(3)}</span>
      </a>`).join("")}</div>` : "";
    article.innerHTML = `
      <div class="message-role">${role === "user" ? "Bạn" : "QualiTrace"}</div>
      <div class="message-content">${renderMarkdown(content)}</div>
      ${sourceHtml}
      ${mode ? `<span class="chat-mode">${escapeHtml(mode.replaceAll("_", " "))}</span>` : ""}`;
    messages.appendChild(article);
    messages.scrollTop = messages.scrollHeight;
    return article;
  };

  stateSelector.addEventListener("click", (event) => {
    const button = event.target.closest("[data-chat-state]");
    if (!button || button.dataset.chatState === chatDataState) return;
    chatDataState = button.dataset.chatState;
    stateSelector.querySelectorAll("button").forEach((item) => item.classList.toggle("active", item === button));
    history.length = 0;
    stateDescription.dataset.state = chatDataState;
    stateDescription.textContent = chatStateDescriptions[chatDataState];
  });

  const checkHealth = async () => {
    try {
      const response = await fetch(`${CHAT_API}/api/health`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const health = await response.json();
      status.textContent = `${health.embedding_provider} retrieval · ${health.llm_provider} LLM · sẵn sàng`;
      statusRow.classList.remove("offline");
    } catch {
      status.textContent = "Chat API đang tắt · hãy mở backend ở cổng 8001";
      statusRow.classList.add("offline");
    }
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message || submit.disabled) return;
    const priorHistory = history.slice(-8);
    addMessage("user", message);
    history.push({ role: "user", content: message });
    input.value = "";
    submit.disabled = true;
    const loading = addMessage("assistant", `Đang truy xuất bằng chứng từ **${stateLabels[chatDataState]}** và tạo câu trả lời…`);
    loading.classList.add("loading");
    try {
      const response = await fetch(`${CHAT_API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history: priorHistory, top_k: 4, data_state: chatDataState }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
      loading.remove();
      addMessage("assistant", payload.answer, payload.sources, payload.mode);
      history.push({ role: "assistant", content: payload.answer });
      status.textContent = `${payload.model} · ${payload.mode.replaceAll("_", " ")}`;
      statusRow.classList.remove("offline");
    } catch (error) {
      loading.remove();
      addMessage("assistant", `Yêu cầu chat thất bại: ${error.message}`);
      statusRow.classList.add("offline");
    } finally {
      submit.disabled = false;
      input.focus();
    }
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  checkHealth();
};

try {
  const data = await loadArtifacts();
  renderKpis(data);
  setupQuestions(data);
  renderMetrics(data);
  renderFreshness(data);
  setupQualityTabs(data);
  renderCorruptionLog(data);
  renderPapers(data);
  setupPresentation(data);
  setupTheme();
  setupChat();
} catch (error) {
  const banner = document.querySelector("#error-banner");
  banner.hidden = false;
  banner.textContent = `Không thể tải artifact cho dashboard: ${error.message}. Hãy chạy demo từ thư mục gốc hoặc dùng npm run dev trong ui/.`;
  console.error(error);
}
