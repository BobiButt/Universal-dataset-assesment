"""
Data Quality & Audit Analyzer
Checks for completeness, consistency, missing fields, and corrupted formats.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

class DataQualityAnalyzer:
    def __init__(self, df: pd.DataFrame = None):
        self.df = df

    def check_tabular_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Audits tabular datasets for missing values, types, and empty records."""
        total_rows, total_cols = df.shape
        missing_per_col = df.isnull().sum().to_dict()
        missing_percentages = (df.isnull().sum() / total_rows * 100).round(2).to_dict()
        
        empty_rows = int((df.isnull().sum(axis=1) == total_cols).sum())
        empty_cols = int((df.isnull().sum(axis=0) == total_rows).sum())
        
        dtype_map = {col: str(dtype) for col, dtype in df.dtypes.items()}
        
        return {
            "total_rows": total_rows,
            "total_columns": total_cols,
            "empty_rows": empty_rows,
            "empty_columns": empty_cols,
            "missing_counts": missing_per_col,
            "missing_percentages": missing_percentages,
            "data_types": dtype_map
        }

    @staticmethod
    def inspect_file_corruption(file_paths: list, modality: str) -> list:
        """Checks media files for corruption."""
        corrupted = []
        if modality == "image":
            from PIL import Image
            for p in file_paths:
                try:
                    with Image.open(p) as img:
                        img.verify()
                except Exception:
                    corrupted.append(p)
        return corrupted