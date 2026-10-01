const fixData = JSON.parse(document.getElementById("fix-data").textContent);
const summary = fixData.summary || {};
const sections = fixData.sections || [];

const fmt = (value) => typeof value === "number" ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : (value ?? "N/A");
const esc = (value) => String(value ?? "").replace(/[&<>"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[char]));
const put = (selector, html) => { const el = document.querySelector(selector); if (el) el.innerHTML = html; };
const metric = ([value, label]) => `<div class="metric"><span class="metric-value">${value}</span><span class="metric-label">${label}</span></div>`;
const detail = ([label, value]) => `<div class="detail"><strong>${value}</strong><span>${label}</span></div>`;

document.getElementById("generated-at").textContent = fixData.generated_at ? `Generated ${fixData.generated_at}` : `Generated ${new Date().toLocaleString()}`;

put("#fix-modalities", (fixData.modalities || []).map((mode) => `<span class="tag">${esc(mode)}</span>`).join(" ") || "unknown");

const outputFiles = (fixData.outputs && fixData.outputs.files) || [];
put("#fix-metrics", [
  [fmt(summary.files_scanned), "Files scanned"],
  [`${fmt(summary.rows_before)} &#8594; ${fmt(summary.rows_after)}`, "Rows (tabular)"],
  [`${fmt(summary.missing_before)} &#8594; ${fmt(summary.missing_after)}`, "Missing cells"],
  [fmt(summary.corrupted_removed), "Corrupted removed"]
].map(metric).join(""));

put("#fix-files", [
  ["Source", esc(fixData.source || "N/A")],
  ["Output folder", esc((fixData.outputs && fixData.outputs.directory) || "data/processed")],
  ["Output files", fmt(outputFiles.length)],
  ["Sections processed", fmt(sections.length)],
  ["Duplicates removed", fmt(summary.duplicates_removed)],
  ["Total actions", fmt(summary.actions)]
].map(detail).join(""));

const links = [];
outputFiles.filter((file) => file.toLowerCase().endsWith(".csv")).slice(0, 8).forEach((file) => {
  links.push(`<a class="button-link" href="/${esc(file)}" download>Download ${esc(file.split("/").pop())}</a>`);
});
if (fixData.report_url) links.push(`<a class="button-link" href="dataset_report.html">Open assessment report</a>`);
put("#fix-links", links.join("") || `<p class="muted">Cleaned outputs were written to the processed folder.</p>`);

const metricRows = (section) => {
  const before = section.before || {};
  const after = section.after || {};
  const keys = Array.from(new Set([...Object.keys(before), ...Object.keys(after)]));
  return keys.map((key) => {
    const b = before[key];
    const a = after[key];
    const delta = (typeof b === "number" && typeof a === "number") ? a - b : null;
    const cls = delta < 0 ? "good-delta" : (delta > 0 ? "warn-delta" : "");
    const change = (delta === null || delta === 0) ? "&#8212;" : `${delta > 0 ? "+" : ""}${delta}`;
    return `<tr><td>${esc(key.replace(/_/g, " "))}</td><td>${fmt(b)}</td><td>${fmt(a)}</td><td class="${cls}">${change}</td></tr>`;
  }).join("");
};

put("#fix-sections", sections.map((section) => {
  const kind = section.kind || "section";
  const title = section.title || section.modality || kind;
  const count = (section.before || {}).files ?? (section.before || {}).rows ?? "";
  const actionHtml = (section.actions || []).map((action) => `<div class="signal ${action.count ? "" : "good"}"><strong>${esc(action.step)}${action.count ? ` (${fmt(action.count)})` : ""}</strong><small>${esc(action.detail)}</small></div>`).join("")
    || `<div class="signal good"><strong>No changes required.</strong><small>Nothing needed fixing in this section.</small></div>`;
  const output = section.output || section.output_dir || "";
  return `<section class="panel">
      <div class="panel-heading"><div><p class="eyebrow">${esc(kind)}</p><h2>${esc(title)}</h2></div><span class="muted">${fmt(count)}</span></div>
      <div class="table-wrap"><table><thead><tr><th>Metric</th><th>Before</th><th>After</th><th>Change</th></tr></thead><tbody>${metricRows(section)}</tbody></table></div>
      <div class="section-actions">${actionHtml}</div>
      ${output ? `<p class="muted">Output: <code>${esc(output)}</code></p>` : ""}
    </section>`;
}).join("") || `<section class="panel"><div class="signal good"><strong>No changes were necessary.</strong><small>The dataset already passed every selected check.</small></div></section>`);

if (fixData.supported_image_formats && fixData.supported_image_formats.length) {
  put("#fix-sections", document.getElementById("fix-sections").innerHTML + `<section class="panel"><p class="eyebrow">Environment</p><p class="muted">Image formats decodable here: ${fixData.supported_image_formats.map(esc).join(", ")}.</p></section>`);
}
