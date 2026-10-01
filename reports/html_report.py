"""Generate a local visual HTML dashboard from assessment results."""

import json
from html import escape
from pathlib import Path
from typing import Any, Dict


class HtmlReportGenerator:
    def generate(self, results: Dict[str, Any], output_path: str = "reports/dataset_report.html") -> str:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        assets_dir = output.parent / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        data_json = json.dumps(results, ensure_ascii=True, default=str).replace("</", "<\\/")
        title = escape(results.get("inventory", {}).get("source_path", "Dataset Assessment"))

        document = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dataset Assessment | {title}</title>
  <link rel="stylesheet" href="assets/report.css">
</head>
<body>
  <main class="shell">
    <header class="hero">
      <div>
        <p class="eyebrow">Universal Dataset Assessment</p>
        <h1>Know the data before the model.</h1>
        <p class="lede">A visual snapshot of inventory, quality, distributions, and readiness.</p>
      </div>
      <div class="hero-meta"><span id="generated-at"></span><button id="download-json" type="button">Download JSON</button></div>
    </header>

    <section class="metrics" id="metrics"></section>

    <section class="grid two-column">
      <article class="panel">
        <div class="panel-heading"><div><p class="eyebrow">Inventory</p><h2>What was found</h2></div></div>
        <div id="inventory-details" class="detail-list"></div>
        <div class="bar-chart" id="modality-chart"></div>
      </article>
      <article class="panel">
        <div class="panel-heading"><div><p class="eyebrow">Quality</p><h2>Data health</h2></div></div>
        <div id="quality-details" class="detail-list"></div>
        <div class="quality-track"><span id="quality-fill"></span></div>
        <p class="muted" id="quality-note"></p>
      </article>
    </section>

    <section class="panel">
      <div class="panel-heading"><div><p class="eyebrow">Statistics</p><h2>Numeric profile</h2></div><span class="muted">Mean, median, spread, and skew</span></div>
      <div class="table-wrap"><table><thead><tr><th>Feature</th><th>Mean</th><th>Median</th><th>Min</th><th>Max</th><th>Skewness</th></tr></thead><tbody id="statistics-table"></tbody></table></div>
    </section>

    <section class="grid two-column">
      <article class="panel"><div class="panel-heading"><div><p class="eyebrow">Risk signals</p><h2>Outliers</h2></div></div><div id="outliers"></div></article>
      <article class="panel"><div class="panel-heading"><div><p class="eyebrow">Readiness</p><h2>Labels and baseline</h2></div></div><div id="readiness"></div></article>
    </section>

    <section class="panel" id="prepare-panel">
      <div class="panel-heading">
        <div><p class="eyebrow">Prepare</p><h2>Clean &amp; optimize for training</h2></div>
        <button id="run-clean" type="button">Clean &amp; Optimize Data</button>
      </div>
      <div class="clean-options">
        <label><input type="checkbox" id="opt-remove-duplicates" checked> Remove duplicate rows</label>
        <label><input type="checkbox" id="opt-fix-missing" checked> Fix missing values</label>
        <label><input type="checkbox" id="opt-drop-empty" checked> Drop empty rows &amp; columns</label>
        <label><input type="checkbox" id="opt-encode"> Encode categoricals for training</label>
        <label><input type="checkbox" id="opt-media" checked> Clean media files (images/audio/video)</label>
        <label class="opt-target">Target column (optional)<input type="text" id="opt-target" placeholder="e.g. mpg"></label>
      </div>
      <div id="clean-status" class="muted">Cleans every modality it finds (tabular, images, audio, video, text) and writes training-ready copies plus a fixed report.</div>
      <div id="clean-actions"></div>
    </section>

    <footer>Raw data was preserved. This dashboard is generated from <code>assessment.json</code>.</footer>
  </main>
  <script id="assessment-data" type="application/json">{data_json}</script>
  <script src="assets/report.js"></script>
</body>
</html>'''
        output.write_text(document, encoding="utf-8")
        return str(output)
