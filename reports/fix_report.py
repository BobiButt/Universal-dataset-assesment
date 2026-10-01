"""Generate the "Fixed Data Report" HTML produced by a cleaning run.

The report reuses the dashboard styling (``assets/report.css``) so it looks
consistent with ``dataset_report.html`` and ships a small script
(``assets/fix_report.js``) that renders the embedded cleaning summary.
"""

import json
from html import escape
from pathlib import Path
from typing import Any, Dict


class FixedReportGenerator:
    def generate(self, result: Dict[str, Any], output_path: str = "reports/dataset_report_fixed.html") -> str:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        assets_dir = output.parent / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        data_json = json.dumps(result, ensure_ascii=True, default=str).replace("</", "<\\/")
        source = escape(str(result.get("source", "dataset")))

        document = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fixed Data Report | {source}</title>
  <link rel="stylesheet" href="assets/report.css">
</head>
<body>
  <main class="shell">
    <header class="hero">
      <div>
        <p class="eyebrow">Training-Ready Export</p>
        <h1>Fixed data report.</h1>
        <p class="lede">Exactly what was cleaned and optimized so the dataset is ready to train on.</p>
      </div>
      <div class="hero-meta"><span id="generated-at"></span><a class="back-link" href="dataset_report.html">&#8592; Back to assessment</a></div>
    </header>

    <section class="metrics" id="fix-metrics"></section>

    <section class="panel">
      <div class="panel-heading"><div><p class="eyebrow">Source</p><h2>Input &amp; output</h2></div><span class="muted" id="fix-modalities"></span></div>
      <div id="fix-files" class="detail-list"></div>
      <div class="clean-links" id="fix-links"></div>
    </section>

    <div id="fix-sections"></div>

    <footer>Raw data was preserved. This report was generated from <code>assessment_fixed.json</code>.</footer>
  </main>
  <script id="fix-data" type="application/json">{data_json}</script>
  <script src="assets/fix_report.js"></script>
</body>
</html>'''
        output.write_text(document, encoding="utf-8")
        return str(output)
