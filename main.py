"""Run the dataset assessment workflow from the command line."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from analysis.data_quality import DataQualityAnalyzer
from analysis.duplicate_detection import DuplicateDetector
from analysis.inspect_dataset import DatasetInspector
from analysis.label_analysis import audit_labels
from analysis.outlier_detection import OutlierDetector
from analysis.statistics import compute_tabular_statistics
from modeling.baseline_model import BaselineModelTrainer
from reports.report_generator import ReportGenerator
from reports.html_report import HtmlReportGenerator

TABULAR_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".json"}


def load_tabular_file(path: Path) -> pd.DataFrame:
    """Load one supported tabular file without modifying the source file."""
    loaders = {
        ".csv": lambda: pd.read_csv(path),
        ".tsv": lambda: pd.read_csv(path, sep="\t"),
        ".xlsx": lambda: pd.read_excel(path),
        ".xls": lambda: pd.read_excel(path),
        ".parquet": lambda: pd.read_parquet(path),
        ".json": lambda: pd.read_json(path),
    }
    try:
        return loaders[path.suffix.lower()]()
    except KeyError as error:
        raise ValueError(f"Unsupported tabular extension: {path.suffix}") from error


def find_first_tabular_file(data_path: Path) -> Optional[Path]:
    """Return the first tabular file in a directory, or the file itself."""
    if data_path.is_file():
        return data_path if data_path.suffix.lower() in TABULAR_EXTENSIONS else None
    return next(
        (path for path in sorted(data_path.rglob("*"))
         if path.is_file() and path.suffix.lower() in TABULAR_EXTENSIONS),
        None,
    )


def run_assessment(data_path: Path, output_dir: Path, target: Optional[str] = None) -> Dict[str, Any]:
    """Run applicable checks and save machine-readable and Markdown results."""
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory = DatasetInspector(str(data_path)).create_inventory()
    results: Dict[str, Any] = {
        "inventory": inventory,
        "source_preserved": True,
        "checks_skipped": [],
    }

    tabular_path = find_first_tabular_file(data_path)
    if tabular_path is None:
        results["checks_skipped"].append("tabular analysis: no supported tabular file found")
        quality: Dict[str, Any] = {"status": "not_run"}
        label_audit_result: Dict[str, Any] = {"status": "not_run"}
        model_result: Dict[str, Any] = {"status": "not_run"}
    else:
        dataframe = load_tabular_file(tabular_path)
        quality = DataQualityAnalyzer().check_tabular_quality(dataframe)
        results["tabular_file"] = str(tabular_path)
        results["statistics"] = compute_tabular_statistics(dataframe)
        results["duplicates"] = DuplicateDetector.detect_tabular_duplicates(dataframe)
        results["outliers"] = OutlierDetector(dataframe).iqr_outliers()

        if target:
            label_audit_result = audit_labels(dataframe, target)
            if target not in dataframe.columns:
                model_result = {"status": "not_run", "reason": "target column not found"}
            else:
                task_type = label_audit_result.get("inferred_task_type", "Classification")
                try:
                    model_result = BaselineModelTrainer(dataframe, target, task_type).train_baseline()
                except (ValueError, TypeError) as error:
                    model_result = {"status": "not_run", "reason": str(error)}
        else:
            label_audit_result = {"status": "not_run", "reason": "pass --target to audit labels"}
            model_result = {"status": "not_run", "reason": "pass --target to train a baseline"}
            results["checks_skipped"].append("label audit and baseline model: no target supplied")

    results["quality"] = quality
    results["label_audit"] = label_audit_result
    results["model"] = model_result

    report_path = output_dir / "dataset_report.md"
    ReportGenerator(inventory, quality, label_audit_result, model_result).generate_markdown_report(str(report_path))
    with (output_dir / "assessment.json").open("w", encoding="utf-8") as result_file:
        json.dump(results, result_file, indent=2, default=str)
    HtmlReportGenerator().generate(results, str(output_dir / "dataset_report.html"))

    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assess a dataset before machine-learning training.")
    parser.add_argument("--data", type=Path, default=Path("data/raw"), help="Dataset file or directory.")
    parser.add_argument("--target", help="Target column; enables label audit and baseline training.")
    parser.add_argument("--output", type=Path, default=Path("reports"), help="Directory for generated reports.")
    parser.add_argument("--clean", action="store_true", help="Run the clean/optimize pipeline and write a training-ready copy.")
    parser.add_argument("--encode", action="store_true", help="One-hot / frequency encode categoricals during --clean.")
    parser.add_argument("--serve", action="store_true", help="Serve the dashboard so the Clean & Optimize button works.")
    parser.add_argument("--port", type=int, default=8000, help="Port used by --serve (default: 8000).")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    results = run_assessment(args.data, args.output, args.target)
    print(json.dumps({
        "source": results["inventory"]["source_path"],
        "files": results["inventory"]["total_files"],
        "modalities": results["inventory"]["detected_modalities"],
        "report": str(args.output / "dataset_report.md"),
        "visual_report": str(args.output / "dataset_report.html"),
        "assessment": str(args.output / "assessment.json"),
    }, indent=2))

    if args.clean:
        from reports.server import run_cleaning

        clean_result = run_cleaning(args.output, target=args.target, options={"encode_categorical": args.encode})
        print(json.dumps({
            "outputs": clean_result["outputs"]["files"],
            "fixed_report": clean_result["report_url"],
            "sections": [
                {
                    "modality": section.get("modality", section.get("kind")),
                    "actions": [action["step"] for action in section.get("actions", [])],
                }
                for section in clean_result["sections"]
            ],
        }, indent=2))

    if args.serve:
        from reports.server import serve

        serve(port=args.port, reports_dir=args.output)


if __name__ == "__main__":
    main()
