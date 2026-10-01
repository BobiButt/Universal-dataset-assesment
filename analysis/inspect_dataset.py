"""
Dataset Inspector & Inventory Generator
Identifies file formats, structure types, modalities, sample counts, and sizes.
"""

import os
import glob
from pathlib import Path
from typing import Dict, Any, List

class DatasetInspector:
    def __init__(self, data_path: str):
        self.data_path = Path(data_path)
        self.supported_extensions = {
            "tabular": [".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".json"],
            "text": [".txt", ".md", ".jsonl", ".xml"],
            "image": [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff"],
            "audio": [".wav", ".mp3", ".flac", ".ogg", ".m4a"],
            "video": [".mp4", ".avi", ".mov", ".mkv"],
        }

    def create_inventory(self) -> Dict[str, Any]:
        """Scans path and returns comprehensive metadata inventory."""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Path does not exist: {self.data_path}")

        files = list(self.data_path.rglob("*")) if self.data_path.is_dir() else [self.data_path]
        file_inventory: List[Dict[str, Any]] = []
        modality_counts: Dict[str, int] = {k: 0 for k in self.supported_extensions.keys()}
        total_size_bytes = 0

        for f in files:
            if f.is_file():
                ext = f.suffix.lower()
                size = f.stat().st_size
                total_size_bytes += size
                
                modality = "unknown"
                for mod, exts in self.supported_extensions.items():
                    if ext in exts:
                        modality = mod
                        modality_counts[mod] += 1
                        break

                file_inventory.append({
                    "name": f.name,
                    "path": str(f),
                    "extension": ext,
                    "size_mb": round(size / (1024 * 1024), 4),
                    "modality": modality
                })

        detected_modalities = [k for k, v in modality_counts.items() if v > 0]
        structure_type = "multimodal" if len(detected_modalities) > 1 else (detected_modalities[0] if detected_modalities else "unknown")

        return {
            "source_path": str(self.data_path),
            "total_files": len(file_inventory),
            "total_size_mb": round(total_size_bytes / (1024 * 1024), 2),
            "structure_type": structure_type,
            "detected_modalities": detected_modalities,
            "modality_counts": modality_counts,
            "file_details": file_inventory[:50]  # Sample first 50 files
        }

if __name__ == "__main__":
    inspector = DatasetInspector("data/raw")
    print(inspector.create_inventory())