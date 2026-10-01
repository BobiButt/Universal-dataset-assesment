const data = JSON.parse(document.getElementById("assessment-data").textContent);
const inventory = data.inventory || {};
const quality = data.quality || {};
const statistics = data.statistics || {};
const labels = data.label_audit || {};
const model = data.model || {};

const format = (value) => typeof value === "number" ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : (value ?? "N/A");
const add = (selector, html) => { document.querySelector(selector).innerHTML = html; };

document.getElementById("generated-at").textContent = `Generated ${new Date().toLocaleString()}`;
add("#metrics", [
  [inventory.total_files ?? 0, "Files scanned"],
  [format(inventory.total_size_mb) + " MB", "Total size"],
  [format(quality.total_rows), "Rows"],
  [format(quality.total_columns), "Columns"]
].map(([value, label]) => `<div class="metric"><span class="metric-value">${value}</span><span class="metric-label">${label}</span></div>`).join(""));

const details = (items) => items.map(([label, value]) => `<div class="detail"><strong>${value}</strong><span>${label}</span></div>`).join("");
add("#inventory-details", details([
  ["Structure", (inventory.structure_type || "unknown").toUpperCase()],
  ["Modalities", (inventory.detected_modalities || []).join(", ") || "None detected"],
  ["Source", inventory.source_path || "N/A"],
  ["Raw data preserved", data.source_preserved ? "Yes" : "Review"]
]));

const modalityCounts = inventory.modality_counts || {};
const maxCount = Math.max(1, ...Object.values(modalityCounts));
add("#modality-chart", Object.entries(modalityCounts).map(([name, count]) => `<div class="bar-row"><span>${name}</span><div class="bar"><i style="width:${(count / maxCount) * 100}%"></i></div><strong>${count}</strong></div>`).join(""));

const missing = Object.values(quality.missing_counts || {}).reduce((sum, value) => sum + Number(value), 0);
const missingRate = quality.total_rows && quality.total_columns ? (missing / (quality.total_rows * quality.total_columns)) * 100 : 0;
add("#quality-details", details([
  ["Empty rows", format(quality.empty_rows)],
  ["Empty columns", format(quality.empty_columns)],
  ["Missing cells", format(missing)],
  ["Data types checked", Object.keys(quality.data_types || {}).length]
]));
document.getElementById("quality-fill").style.width = `${Math.min(100, missingRate)}%`;
document.getElementById("quality-note").textContent = missing ? `${missingRate.toFixed(1)}% of cells are missing. Review before training.` : "No missing cells were reported in the quality scan.";

const numeric = statistics.numerical_stats || {};
add("#statistics-table", Object.entries(numeric).map(([name, values]) => `<tr><td title="${name}">${name}</td><td>${format(values.mean)}</td><td>${format(values.median)}</td><td>${format(values.min)}</td><td>${format(values.max)}</td><td>${format(values.skewness)}</td></tr>`).join("") || `<tr><td colspan="6">No numerical statistics were generated.</td></tr>`);

const outliers = data.outliers || {};
add("#outliers", Object.entries(outliers).map(([name, value]) => `<div class="signal ${value.count === 0 ? "good" : ""}"><strong>${name}: ${format(value.count)} outliers</strong><small>${value.recommendation || "Review this feature."}</small></div>`).join("") || `<div class="signal good"><strong>No outlier results</strong><small>This check was not applicable.</small></div>`);
add("#readiness", [
  ["Labels", labels.status === "not_run" ? labels.reason : `${labels.inferred_task_type || "Detected"} task`],
  ["Baseline", model.status === "not_run" ? model.reason : `${model.model}: ${model.metric} ${model.score}`],
  ["Skipped checks", (data.checks_skipped || []).join("; ") || "None"]
].map(([label, value]) => `<div class="signal"><strong>${label}</strong><small>${value}</small></div>`).join(""));

document.getElementById("download-json").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = "assessment.json"; link.click(); URL.revokeObjectURL(link.href);
});

const runCleanButton = document.getElementById("run-clean");
const cleanStatus = document.getElementById("clean-status");
const cleanActions = document.getElementById("clean-actions");

const renderCleanResult = (result) => {
  const summary = result.summary || {};
  const sections = result.sections || [];
  const outputFiles = (result.outputs && result.outputs.files) || [];
  cleanStatus.className = "";
  const parts = [];
  if (summary.rows_before || summary.rows_after) parts.push(`rows ${format(summary.rows_before)} &#8594; ${format(summary.rows_after)}`);
  if (summary.missing_before) parts.push(`missing cells ${format(summary.missing_before)} &#8594; ${format(summary.missing_after)}`);
  if (summary.media_files_before) parts.push(`media files ${format(summary.media_files_before)} &#8594; ${format(summary.media_files_after)}`);
  cleanStatus.innerHTML = `<strong>Cleaned successfully.</strong> ${parts.join(", ")}${parts.length ? "." : ""} ${sections.length} section(s) processed, ${outputFiles.length} output file(s) written.`;
  cleanActions.innerHTML = sections.map((section) => {
    const title = section.title || section.modality || section.kind;
    const steps = (section.actions || []).map((action) => action.step).join(", ") || "no changes";
    return `<div class="signal good"><strong>${title}</strong><small>${steps}</small></div>`;
  }).join("");
  const links = [];
  if (result.report_url) links.push(`<a class="button-link" href="${result.report_url}" target="_blank" rel="noopener">Open fixed report</a>`);
  outputFiles.filter((file) => file.toLowerCase().endsWith(".csv")).slice(0, 5).forEach((file) => {
    links.push(`<a class="button-link" href="/${file}" download>Download ${file.split("/").pop()}</a>`);
  });
  cleanActions.insertAdjacentHTML("beforeend", `<div class="clean-links">${links.join("")}</div>`);
};

const renderCleanError = (message) => {
  cleanActions.innerHTML = "";
  cleanStatus.className = "muted";
  if (window.location.protocol === "file:") {
    cleanStatus.innerHTML = "Start the local server to enable cleaning: run <code>python main.py --serve</code>, then open <code>http://127.0.0.1:8000/reports/dataset_report.html</code>.";
  } else {
    cleanStatus.innerHTML = `Could not clean the data: <strong>${message}</strong>`;
  }
};

runCleanButton?.addEventListener("click", async () => {
  const payload = {
    source: data.tabular_file || undefined,
    target: document.getElementById("opt-target")?.value.trim() || undefined,
    drop_duplicates: document.getElementById("opt-remove-duplicates").checked,
    fix_missing: document.getElementById("opt-fix-missing").checked,
    drop_empty_columns: document.getElementById("opt-drop-empty").checked,
    drop_empty_rows: document.getElementById("opt-drop-empty").checked,
    encode_categorical: document.getElementById("opt-encode").checked,
    include_media: document.getElementById("opt-media")?.checked ?? true
  };
  runCleanButton.disabled = true;
  runCleanButton.textContent = "Cleaning...";
  cleanStatus.className = "muted";
  cleanStatus.textContent = "Running the cleaning pipeline...";
  try {
    const response = await fetch("/api/clean", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok || result.status === "error") throw new Error(result.error || `HTTP ${response.status}`);
    renderCleanResult(result);
  } catch (error) {
    renderCleanError(error.message);
  } finally {
    runCleanButton.disabled = false;
    runCleanButton.textContent = "Clean & Optimize Data";
  }
});
