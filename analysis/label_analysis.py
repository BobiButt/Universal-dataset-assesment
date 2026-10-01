"""
Label Validation and Ground Truth Auditor
"""

import pandas as pd
from typing import Dict, Any

def audit_labels(df: pd.DataFrame, target_column: str) -> Dict[str, Any]:
    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found"}

    counts = df[target_column].value_counts(dropna=False).to_dict()
    missing = int(df[target_column].isnull().sum())
    total = len(df)
    
    is_continuous = pd.api.types.is_numeric_dtype(df[target_column]) and df[target_column].nunique() > 20
    task_type = "Regression" if is_continuous else "Classification"

    imbalance_ratio = None
    if task_type == "Classification" and len(counts) > 1:
        max_c = max([v for k, v in counts.items() if pd.notnull(k)])
        min_c = min([v for k, v in counts.items() if pd.notnull(k)])
        imbalance_ratio = round(max_c / max(min_c, 1), 2)

    return {
        "target_column": target_column,
        "inferred_task_type": task_type,
        "missing_labels": missing,
        "class_counts": counts,
        "imbalance_ratio": imbalance_ratio,
        "is_imbalanced": (imbalance_ratio > 3.0) if imbalance_ratio else False
    }