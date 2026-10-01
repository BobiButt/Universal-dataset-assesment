"""Local preview + data-cleaning server for the assessment dashboard.

Uses only the Python standard library (``http.server``) so the project needs
no extra dependency. Serving the dashboard over HTTP lets the report's
"Clean & Optimize Data" button call ``POST /api/clean``, which cleans every
supported modality (tabular, images, audio, video, text), writes training-ready
copies to ``data/processed`` and generates ``reports/dataset_report_fixed.html``.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

from preprocessing.optimize_dataset import optimize_dataset
from reports.fix_report import FixedReportGenerator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Options accepted from the browser and forwarded to the cleaning engine.
ALLOWED_OPTIONS = {
    "fix_missing",
    "drop_duplicates",
    "drop_empty_columns",
    "drop_empty_rows",
    "missing_threshold",
    "numerical_strategy",
    "categorical_strategy",
    "coerce_numeric",
    "strip_column_names",
    "strip_strings",
    "encode_categorical",
    "max_one_hot_cardinality",
    "include_media",
    "max_image_size",
    "convert_images",
}

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".ico": "image/x-icon",
}


def _resolve(path: Path) -> Path:
    """Resolve a path against the project root when it is relative."""
    path = Path(path)
    return path if path.is_absolute() else (PROJECT_ROOT / path)


def _rel(path: Path) -> str:
    """Return a POSIX path relative to the project root (for URLs)."""
    path = Path(path).resolve()
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _source_path_from_assessment(reports_dir: Path) -> Optional[Path]:
    assessment = reports_dir / "assessment.json"
    if not assessment.exists():
        return None
    try:
        data = json.loads(assessment.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    source_path = (data.get("inventory") or {}).get("source_path") or data.get("tabular_file")
    if not source_path:
        return None
    candidate = _resolve(source_path)
    return candidate if candidate.exists() else None


def find_default_source_path(reports_dir: Path) -> Optional[Path]:
    """Pick the dataset to clean: the assessed source, else the ``data/raw`` folder."""
    reports_dir = _resolve(reports_dir)
    candidate = _source_path_from_assessment(reports_dir)
    if candidate is not None:
        return candidate
    raw_dir = PROJECT_ROOT / "data" / "raw"
    return raw_dir if raw_dir.is_dir() else None


def _relativize_outputs(result: Dict[str, Any]) -> None:
    """Convert absolute output paths into project-relative paths for URLs."""
    outputs = result.get("outputs", {})
    if outputs.get("directory"):
        outputs["directory"] = _rel(Path(outputs["directory"]))
    outputs["files"] = [_rel(Path(path)) for path in outputs.get("files", [])]
    for section in result.get("sections", []):
        for key in ("output", "output_dir", "source", "source_dir"):
            if section.get(key):
                section[key] = _rel(Path(section[key]))
        for removed in section.get("removed", []):
            if removed.get("file"):
                removed["file"] = _rel(Path(removed["file"]))


def run_cleaning(
    reports_dir: Path,
    *,
    source: Optional[str] = None,
    target: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Clean every supported modality, export it, and write the fixed report."""
    reports_dir = _resolve(reports_dir)

    source_path = _resolve(source) if source else find_default_source_path(reports_dir)
    if source_path is None or not Path(source_path).exists():
        raise FileNotFoundError("No dataset was found to clean.")

    result = optimize_dataset(
        Path(source_path),
        PROCESSED_DIR,
        target=target,
        options=dict(options or {}),
    )
    result["source"] = _rel(source_path)
    result["report_url"] = "/" + _rel(reports_dir / "dataset_report_fixed.html")
    _relativize_outputs(result)

    FixedReportGenerator().generate(result, str(reports_dir / "dataset_report_fixed.html"))
    with (reports_dir / "assessment_fixed.json").open("w", encoding="utf-8") as summary_file:
        json.dump(result, summary_file, indent=2, default=str)
    return result


def make_handler(reports_dir: Path):
    """Build a request handler bound to the report output directory."""
    reports_dir = _resolve(reports_dir)
    dashboard_url = "/" + _rel(reports_dir / "dataset_report.html")

    class DashboardRequestHandler(BaseHTTPRequestHandler):
        server_version = "DatasetDashboard/1.0"

        def log_message(self, *args: Any) -> None:  # keep the console quiet
            pass

        def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
            body = json.dumps(payload, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _serve_file(self, url_path: str) -> None:
            target = (PROJECT_ROOT / url_path.lstrip("/")).resolve()
            if not target.is_relative_to(PROJECT_ROOT) or not target.exists():
                self.send_error(404, "Not found")
                return
            if target.is_dir():
                target = target / "index.html"
                if not target.exists():
                    self.send_error(404, "Not found")
                    return
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", MIME_TYPES.get(target.suffix.lower(), "application/octet-stream"))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
            url_path = unquote(urlparse(self.path).path)
            if url_path in ("", "/"):
                self.send_response(302)
                self.send_header("Location", dashboard_url)
                self.end_headers()
                return
            if url_path == "/api/status":
                default_source = find_default_source_path(reports_dir)
                self._send_json({
                    "status": "ok",
                    "reports_dir": _rel(reports_dir),
                    "default_source": _rel(default_source) if default_source else None,
                })
                return
            self._serve_file(url_path)

        def do_POST(self) -> None:  # noqa: N802 (stdlib naming)
            url_path = urlparse(self.path).path
            if url_path != "/api/clean":
                self._send_json({"status": "error", "error": "Unknown endpoint."}, status=404)
                return
            length = int(self.headers.get("Content-Length") or 0)
            raw_body = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw_body or b"{}")
            except json.JSONDecodeError:
                payload = {}
            options = {key: value for key, value in payload.items() if key in ALLOWED_OPTIONS}
            try:
                result = run_cleaning(
                    reports_dir,
                    source=payload.get("source"),
                    target=payload.get("target") or None,
                    options=options,
                )
            except Exception as error:  # surface any failure to the button
                self._send_json({"status": "error", "error": str(error)}, status=400)
                return
            self._send_json(result)

    return DashboardRequestHandler


def serve(port: int = 8000, reports_dir: Path = "reports") -> None:
    """Run the dashboard server until interrupted (Ctrl+C)."""
    handler = make_handler(reports_dir)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{port}/" + _rel(_resolve(reports_dir) / "dataset_report.html")
    print(f"Serving dataset dashboard at {url}")
    print("Click 'Clean & Optimize Data' in the browser. Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        httpd.server_close()

