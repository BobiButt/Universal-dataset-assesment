"""
Error Analysis Module
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

def analyze_prediction_errors(y_true: np.ndarray, y_pred: np.ndarray, task_type: str = "Classification") -> Dict[str, Any]:
    if task_type == "Classification":
        mismatches = np.where(y_true != y_pred)[0]
        return {
            "total_errors": len(mismatches),
            "error_rate": round(len(mismatches) / len(y_true), 4),
            "mismatch_indices": mismatches[:20].tolist()
        }
    else:
        residuals = y_true - y_pred
        return {
            "mean_residual": float(np.mean(residuals)),
            "std_residual": float(np.std(residuals)),
            "max_error": float(np.max(np.abs(residuals)))
        }