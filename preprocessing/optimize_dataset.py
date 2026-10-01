"""
End-to-end cleaning & optimization for tabular, media, and mixed datasets.

``optimize_dataset`` inspects a file or directory, cleans every supported
modality it finds (tabular tables plus images/audio/video/text), writes the
results into ``data/processed`` and returns a unified report that powers the
"fixed data" HTML report.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from analysis.inspect_dataset import DatasetInspector
from preprocessing.clean_data import DataCleaner
from preprocessing.media_preprocessing import (
    IMAGE_EXTENSION_BLOCKLIST,
    clean_media_files,
    supported_image_formats,
)

TABULAR_LOADERS = {
    ".csv": lambda path: pd.read_csv(path),
    ".tsv": lambda path: pd.read_csv(path, sep="\t"),
    ".xlsx": lambda path: pd.read_excel(path),
    ".xls": lambda path: pd.read_excel(path),
    ".parquet": lambda path: pd.read_parquet(path),
    ".json": lambda path: pd.read_json(path),
}

MEDIA_MODALITIES = ("image", "audio", "video", "text")
MODALITY_DIRS = {"image": "images", "audio": "audio", "video": "video", "text": "text"}

TABULAR_OPTION_KEYS = {
    "target", "fix_missing", "drop_duplicates", "drop_empty_columns",
    "drop_empty_rows", "missing_threshold", "numerical_strategy",
    "categorical_strategy", "coerce_numeric", "strip_column_names",
    "strip_strings", "encode_categorical", "max_one_hot_cardinality",
}


def supported_extensions() -> Dict[str, List[str]]:
    """Extension map that also covers every image format Pillow can decode."""
    base = {modality: set(exts) for modality, exts in DatasetInspector(".").supported_extensions.items()}
    try:
        from PIL import Image

        Image.init()
        base["image"] |= {ext.lower() for ext in Image.registered_extensions()}
    except ImportError:  # pragma: no cover - Pillow is a hard requirement
        pass
    base["image"] -= IMAGE_EXTENSION_BLOCKLIST
    base["text"] |= {".html", ".htm", ".rst", ".log", ".yaml", ".yml", ".ini", ".cfg", ".text"}
    return {modality: sorted(exts) for modality, exts in base.items()}


def load_tabular_file(path: Path) -> pd.DataFrame:
    """Load one supported tabular file without modifying the source."""
    path = Path(path)
    loader = TABULAR_LOADERS.get(path.suffix.lower())
    if loader is None:
        raise ValueError(f"Unsupported tabular extension: {path.suffix}")
    return loader(path)


def iter_files_by_modality(data_path: Path, supported_extensions: Dict[str, List[str]]) -> Dict[str, List[Path]]:
    """Group every file under a path by its detected modality."""
    data_path = Path(data_path)
    buckets: Dict[str, List[Path]] = {modality: [] for modality in supported_extensions}
    files = list(data_path.rglob("*")) if data_path.is_dir() else [data_path]
    for path in sorted(files):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        for modality, extensions in supported_extensions.items():
            if suffix in extensions:
                buckets[modality].append(path)
                break
    return buckets


def _summarize(sections: List[Dict[str, Any]], inventory: Dict[str, Any]) -> Dict[str, Any]:
    summary = {
        "files_scanned": inventory.get("total_files", 0),
        "tabular_files": 0,
        "media_files_before": 0,
        "media_files_after": 0,
        "rows_before": 0,
        "rows_after": 0,
        "missing_before": 0,
        "missing_after": 0,
        "duplicates_removed": 0,
        "corrupted_removed": 0,
        "actions": 0,
    }
    for section in sections:
        summary["actions"] += len(section.get("actions", []))
        before = section.get("before", {})
        after = section.get("after", {})
        if section.get("kind") == "tabular":
            summary["tabular_files"] += 1
            summary["rows_before"] += int(before.get("rows", 0) or 0)
            summary["rows_after"] += int(after.get("rows", 0) or 0)
            summary["missing_before"] += int(before.get("missing_cells", 0) or 0)
            summary["missing_after"] += int(after.get("missing_cells", 0) or 0)
            summary["duplicates_removed"] += int(section.get("duplicates_removed", 0) or 0)
        else:
            summary["media_files_before"] += int(before.get("files", 0) or 0)
            summary["media_files_after"] += int(after.get("files", 0) or 0)
            summary["corrupted_removed"] += int(before.get("corrupted", 0) or 0)
            summary["duplicates_removed"] += int(before.get("duplicates", 0) or 0)
    return summary


def optimize_dataset(
    source: Path,
    processed_root: Path,
    *,
    target: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Clean every supported modality under ``source`` into ``processed_root``."""
    source = Path(source)
    processed_root = Path(processed_root)
    options = dict(options or {})

    include_media = bool(options.pop("include_media", True))
    max_image_size = options.pop("max_image_size", None)
    convert_images = bool(options.pop("convert_images", True))
    image_format = options.pop("image_format", "PNG")
    tabular_options = {key: value for key, value in options.items() if key in TABULAR_OPTION_KEYS}

    inspector = DatasetInspector(str(source))
    inventory = inspector.create_inventory()
    buckets = iter_files_by_modality(source, supported_extensions())
    detected_modalities = [
        modality for modality in ("tabular", "text", "image", "audio", "video")
        if buckets.get(modality)
    ]

    sections: List[Dict[str, Any]] = []
    outputs: List[Path] = []

    for path in buckets.get("tabular", []):
        try:
            dataframe = load_tabular_file(path)
            cleaned, report = DataCleaner(dataframe).optimize_for_training(target=target, **tabular_options)
            processed_root.mkdir(parents=True, exist_ok=True)
            out_path = processed_root / f"{path.stem}_cleaned.csv"
            cleaned.to_csv(out_path, index=False)
            outputs.append(out_path)
            section: Dict[str, Any] = {
                "kind": "tabular",
                "title": path.name,
                "source": str(path),
                "output": str(out_path),
            }
            section.update(report)
            sections.append(section)
        except Exception as error:  # noqa: BLE001 - one bad file must not abort the run
            sections.append({
                "kind": "tabular",
                "title": path.name,
                "source": str(path),
                "status": "error",
                "error": str(error),
                "before": {},
                "after": {},
                "actions": [{"step": "Failed to clean", "detail": str(error), "count": 0}],
            })

    if include_media:
        for modality in MEDIA_MODALITIES:
            paths = buckets.get(modality, [])
            if not paths:
                continue
            section = clean_media_files(
                paths,
                modality,
                processed_root / MODALITY_DIRS[modality],
                convert_images=convert_images,
                image_format=image_format,
                max_image_size=max_image_size,
            )
            section["source_dir"] = str(source)
            sections.append(section)
            outputs.extend(Path(path) for path in section["outputs"])

    result: Dict[str, Any] = {
        "status": "ok",
        "source": str(source),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "modalities": detected_modalities,
        "supported_image_formats": supported_image_formats(),
        "summary": _summarize(sections, inventory),
        "sections": sections,
        "outputs": {
            "directory": str(processed_root),
            "files": sorted(str(path) for path in outputs),
        },
    }
    return result

