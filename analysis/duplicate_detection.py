"""
Exact and Near-Duplicate Detector
"""

import pandas as pd
import hashlib
from typing import Dict, List, Any

class DuplicateDetector:
    @staticmethod
    def detect_tabular_duplicates(df: pd.DataFrame, subset: List[str] = None) -> Dict[str, Any]:
        exact_dups = int(df.duplicated(subset=subset).sum())
        return {
            "exact_duplicate_rows": exact_dups,
            "duplicate_percentage": round((exact_dups / len(df)) * 100, 2) if len(df) > 0 else 0.0
        }

    @staticmethod
    def detect_file_duplicates(file_paths: List[str]) -> List[List[str]]:
        """Identifies binary exact duplicate files via MD5 hashing."""
        hashes = {}
        duplicates = []
        for path in file_paths:
            try:
                with open(path, "rb") as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                if file_hash in hashes:
                    hashes[file_hash].append(path)
                else:
                    hashes[file_hash] = [path]
            except Exception:
                continue
        
        return [group for group in hashes.values() if len(group) > 1]