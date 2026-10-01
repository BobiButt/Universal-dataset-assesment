"""
Media Modality Preprocessor (images, audio, video, text)

Validates, de-duplicates, and (optionally) normalizes non-tabular files so a
mixed dataset can be exported into a consistent ``data/processed`` layout that
is ready for model training.

Only Pillow (already a project dependency) and the Python standard library are
used, so no extra install is required.
"""

import hashlib
import shutil
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from PIL import Image
except ImportError:  # pragma: no cover - Pillow is a hard requirement
    Image = None

from preprocessing.text_preprocessing import clean_text_content

# Pillow registers some document/non-raster formats we do not treat as images.
IMAGE_EXTENSION_BLOCKLIST = {
    ".pdf", ".eps", ".ps", ".mpeg", ".mpg", ".h5", ".hdf", ".grib",
    ".fits", ".fit", ".bufr", ".palm", ".dcx", ".fli", ".flc",
}

# Magic-byte signatures for containers we can sanity-check without codecs.
_AUDIO_SIGNATURES: Dict[str, Tuple[bytes, int]] = {
    "wav": (b"RIFF", 0),
    "mp3": (b"ID3", 0),
    "ogg": (b"OggS", 0),
    "flac": (b"fLaC", 0),
}
_VIDEO_SIGNATURES: Dict[str, Tuple[bytes, int]] = {
    "mp4": (b"ftyp", 4),
    "m4v": (b"ftyp", 4),
    "mov": (b"ftyp", 4),
    "avi": (b"AVI ", 8),
    "mkv": (b"\x1a\x45\xdf\xa3", 0),
    "webm": (b"\x1a\x45\xdf\xa3", 0),
}


def supported_image_formats() -> List[str]:
    """Return the image formats Pillow can decode in this environment."""
    if Image is None:
        return []
    Image.init()
    formats = {
        fmt for ext, fmt in Image.registered_extensions().items()
        if ext.lower() not in IMAGE_EXTENSION_BLOCKLIST
    }
    return sorted(formats)


def file_digest(path: Path) -> str:
    """Content hash used to detect byte-for-byte duplicate files."""
    digest = hashlib.md5()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_image(path: Path) -> Tuple[bool, str]:
    if Image is None:
        return True, ""
    try:
        with Image.open(path) as image:
            image.verify()
        return True, ""
    except Exception as error:  # noqa: BLE001 - surface the reason to the report
        return False, str(error)


def validate_audio(path: Path) -> Tuple[bool, str]:
    if path.stat().st_size == 0:
        return False, "empty file"
    suffix = path.suffix.lower().lstrip(".")
    if suffix == "wav":
        try:
            with wave.open(str(path), "rb") as handle:
                if handle.getnframes() <= 0:
                    return False, "wav file has no audio frames"
            return True, ""
        except Exception as error:  # noqa: BLE001
            return False, str(error)
    with open(path, "rb") as handle:
        header = handle.read(12)
    if _AUDIO_SIGNATURES.get(suffix) and header.startswith(_AUDIO_SIGNATURES[suffix][0]):
        return True, ""
    if suffix == "m4a" and header[4:8] == b"ftyp":
        return True, ""
    if suffix == "mp3" and header[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return True, ""
    return True, ""  # unknown-but-present format: keep it, avoid false negatives


def validate_video(path: Path) -> Tuple[bool, str]:
    if path.stat().st_size == 0:
        return False, "empty file"
    suffix = path.suffix.lower().lstrip(".")
    signature = _VIDEO_SIGNATURES.get(suffix)
    if signature is None:
        return True, ""
    marker, offset = signature
    with open(path, "rb") as handle:
        handle.seek(offset)
        return (handle.read(len(marker)) == marker), "unrecognized video header"


def validate_media_file(path: Path, modality: str) -> Tuple[bool, str]:
    if modality == "image":
        return validate_image(path)
    if modality == "audio":
        return validate_audio(path)
    if modality == "video":
        return validate_video(path)
    return True, ""


def _unique_target(directory: Path, name: str, used: set) -> Path:
    candidate = directory / name
    stem, suffix = candidate.stem, candidate.suffix
    counter = 1
    while candidate.name in used or candidate.exists():
        candidate = directory / f"{stem}_{counter}{suffix}"
        counter += 1
    used.add(candidate.name)
    return candidate


def clean_media_files(
    paths: List[Path],
    modality: str,
    output_dir: Path,
    *,
    convert_images: bool = True,
    image_format: str = "PNG",
    max_image_size: Optional[int] = None,
) -> Dict[str, Any]:
    """Validate, de-duplicate, and export media files into ``output_dir``.

    Returns a report section describing exactly what was changed.
    """
    paths = [Path(path) for path in paths]
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    actions: List[Dict[str, Any]] = []
    removed: List[Dict[str, str]] = []
    outputs: List[Path] = []
    seen_hashes: Dict[str, str] = {}
    valid: List[Path] = []
    corrupted = 0
    duplicates = 0

    for path in paths:
        ok, error = validate_media_file(path, modality)
        if not ok:
            corrupted += 1
            removed.append({"file": str(path), "reason": f"corrupted: {error}"})
            continue
        digest = file_digest(path)
        if digest in seen_hashes:
            duplicates += 1
            removed.append({"file": str(path), "reason": f"duplicate of {seen_hashes[digest]}"})
            continue
        seen_hashes[digest] = str(path)
        valid.append(path)

    if corrupted:
        actions.append({
            "step": f"Validate {modality} files",
            "detail": f"Checked {len(paths)} file(s); {corrupted} unreadable/corrupted removed.",
            "count": corrupted,
        })
    else:
        actions.append({
            "step": f"Validate {modality} files",
            "detail": f"All {len(paths)} file(s) opened successfully.",
            "count": 0,
        })

    if duplicates:
        actions.append({
            "step": "Remove duplicate files",
            "detail": f"Removed {duplicates} byte-identical duplicate(s).",
            "count": duplicates,
        })

    used_names: set = set()
    converted = 0
    copied = 0
    text_cleaned = 0
    for path in valid:
        try:
            if modality == "image" and convert_images and Image is not None:
                target = _unique_target(output_dir, path.stem + ".png", used_names)
                with Image.open(path) as image:
                    image = image.convert("RGB")
                    if max_image_size:
                        image.thumbnail((max_image_size, max_image_size), Image.Resampling.LANCZOS)
                    image.save(target, image_format)
                outputs.append(target)
                converted += 1
                continue
            if modality == "text":
                target = _unique_target(output_dir, path.stem + ".txt", used_names)
                raw = path.read_text(encoding="utf-8", errors="ignore")
                target.write_text(clean_text_content(raw, lower=False, remove_html=True), encoding="utf-8")
                outputs.append(target)
                text_cleaned += 1
                continue
            target = _unique_target(output_dir, path.name, used_names)
            shutil.copy2(path, target)
            outputs.append(target)
            copied += 1
        except Exception as error:  # noqa: BLE001
            removed.append({"file": str(path), "reason": f"failed to export: {error}"})

    if modality == "image" and converted:
        note = f"Converted {converted} image(s) to {image_format} (RGB)"
        if max_image_size:
            note += f", longest side <= {max_image_size}px"
        actions.append({"step": "Normalize images", "detail": note + ".", "count": converted})
    if modality == "text" and text_cleaned:
        actions.append({
            "step": "Clean text content",
            "detail": f"Stripped HTML/whitespace from {text_cleaned} text file(s).",
            "count": text_cleaned,
        })
    if copied:
        actions.append({
            "step": f"Copy {modality} files",
            "detail": f"Copied {copied} file(s) unchanged into the processed folder.",
            "count": copied,
        })

    after_files = len(outputs)
    if not actions:
        actions.append({
            "step": "No changes required",
            "detail": "No valid files of this modality were found.",
            "count": 0,
        })

    return {
        "kind": "media",
        "modality": modality,
        "title": modality.capitalize(),
        "output_dir": str(output_dir),
        "before": {"files": len(paths), "corrupted": corrupted, "duplicates": duplicates},
        "after": {"files": after_files, "corrupted": 0, "duplicates_removed": duplicates},
        "actions": actions,
        "removed": removed,
        "outputs": [str(path) for path in outputs],
    }

