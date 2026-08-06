const DATA_ROOT = "../data";

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
  papers: `${DATA_ROOT}/clean/papers_clean.json`,
  manifest: `${DATA_ROOT}/embeddings/papers_embeddings.json`,
};

const stateLabels = {
  baseline: "Baseline",
  corrupted: "Corrupted",
  repaired: "Repaired",
};

const fetchJson = async (path) => {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${path} returned HTTP ${response.status}`);
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

const renderKpis = (data) => {
  const baselineQuality = data.quality.baseline.summary;
  const corruptedQuality = data.quality.corrupted.summary;
  const repaired = data.metrics.repaired;
  const baseline = data.metrics.baseline;
  const recoveryMetrics = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy"];
  const recovered = recoveryMetrics.filter((key) => repaired[key] >= baseline[key]).length;
  const repairRate = recovered / recoveryMetrics.length;

  document.querySelector("#total-records").textContent = data.papers.length.toLocaleString();
  document.querySelector("#record-meta").textContent = `${data.manifest.documents.length} vectors · ${data.manifest.embedding_dimension} dimensions`;
  const qualityRate = baselineQuality.passed / baselineQuality.total_checks;
  document.querySelector("#quality-rate").textContent = percent(qualityRate);
  document.querySelector("#quality-meter").style.width = percent(qualityRate);
  document.querySelector("#corruption-signals").textContent = corruptedQuality.failed;
  document.querySelector("#corruption-meta").textContent = `${data.corruptionLog.entries.length} scenarios · ${corruptedQuality.total_checks} gates`;
  document.querySelector("#repair-rate").textContent = percent(repairRate);
  document.querySelector("#repair-meta").textContent = `${data.quality.repaired.summary.passed}/${data.quality.repaired.summary.total_checks} quality gates pass`;
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
          <span class="status-chip ${item.retrieval_hit ? "success" : "danger"}">${item.retrieval_hit ? "Hit" : "Miss"}</span>
        </div>
        <p class="state-answer">${escapeHtml(item.answer)}</p>
        <div class="state-footer">
          <div class="retrieval-line">${item.retrieved_doc_ids.length} papers · ${escapeHtml(item.retrieved_doc_ids[0] || "No result")}</div>
          <div class="mini-metrics">
            <div class="mini-metric"><span>Token F1</span><strong>${item.token_f1.toFixed(2)}</strong></div>
            <div class="mini-metric"><span>Judge</span><strong>${score}/5</strong></div>
            <div class="mini-metric"><span>Backend</span><strong>${escapeHtml(item.judge_backend.replace("llm:", ""))}</strong></div>
          </div>
        </div>
      </article>`;
  }).join("");
};

const setupQuestions = (data) => {
  const select = document.querySelector("#question-select");
  select.innerHTML = data.answers.baseline.map((item, index) =>
    `<option value="${index}">${escapeHtml(item.id)} · ${escapeHtml(item.question_type)}</option>`
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
    ["Retrieval hit", "retrieval_hit_rate"],
    ["Token F1", "mean_token_f1"],
    ["Judge accuracy", "judge_accuracy"],
    ["Judge score", "mean_judge_score", 5],
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
      <span><i style="background:var(--success)"></i>Baseline</span>
      <span><i style="background:var(--danger)"></i>Corrupted</span>
      <span><i style="background:var(--repair)"></i>Repaired</span>
    </div>`;
};

const renderFreshness = (data) => {
  const current = data.freshness.repaired;
  const corrupted = data.freshness.corrupted;
  const status = document.querySelector("#freshness-status");
  status.textContent = current.is_fresh ? "Healthy" : "Stale";
  status.classList.add(current.is_fresh ? "success" : "danger");
  document.querySelector("#freshness-age").textContent = current.threshold_days;
  document.querySelector("#freshness-details").innerHTML = `
    <div><dt>Latest publication</dt><dd>${escapeHtml(current.latest_published)}</dd></div>
    <div><dt>Oldest publication</dt><dd>${escapeHtml(current.oldest_published)}</dd></div>
    <div><dt>Corrupted stale rows</dt><dd>${corrupted.stale_rows}</dd></div>
    <div><dt>Repaired stale rows</dt><dd>${current.stale_rows}</dd></div>`;
  document.querySelector("#artifact-time").textContent = `Snapshot · ${new Date(current.generated_at_utc).toLocaleString()}`;
};

const renderQuality = (data, state) => {
  const report = data.quality[state];
  document.querySelector("#quality-summary").innerHTML = `
    <span class="quality-score">${report.summary.passed}/${report.summary.total_checks}</span>
    <span>${stateLabels[state]} checks passed · ${report.summary.failed} failure${report.summary.failed === 1 ? "" : "s"}</span>`;
  document.querySelector("#quality-table").innerHTML = report.checks.map((check) => `
    <tr>
      <td>${escapeHtml(check.check)}</td>
      <td>${escapeHtml(check.quality_dimension)}</td>
      <td>${escapeHtml(check.observed)}</td>
      <td>${escapeHtml(check.expected)}</td>
      <td><span class="check-status ${check.passed ? "pass" : "fail"}">${check.passed ? "PASS" : "FAIL"}</span></td>
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
  document.querySelector("#corruption-count").textContent = `${data.corruptionLog.entries.length} scenarios`;
  document.querySelector("#corruption-timeline").innerHTML = data.corruptionLog.entries.map((entry) => `
    <div class="timeline-item">
      <div class="timeline-title"><span>${escapeHtml(entry.corruption)}</span><span>×${entry.count}</span></div>
      <p class="timeline-description">${escapeHtml(entry.description)}</p>
    </div>`).join("");
};

const renderPapers = (data) => {
  document.querySelector("#paper-list").innerHTML = data.papers.slice(0, 5).map((paper) => `
    <div class="paper-item">
      <a href="${escapeHtml(paper.abs_url)}" target="_blank" rel="noreferrer">${escapeHtml(paper.title)}</a>
      <div class="paper-meta">${escapeHtml(paper.paper_id)} · ${escapeHtml(paper.published)} · ${escapeHtml(paper.primary_category)}</div>
    </div>`).join("");
};

const setupTheme = () => {
  document.querySelector("#theme-toggle").addEventListener("click", () => {
    document.documentElement.classList.toggle("dark");
  });
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
  setupTheme();
} catch (error) {
  const banner = document.querySelector("#error-banner");
  banner.hidden = false;
  banner.textContent = `Unable to load dashboard artifacts: ${error.message}. Start the demo from the repository root or run npm run dev inside ui/.`;
  console.error(error);
}
