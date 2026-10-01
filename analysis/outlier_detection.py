"""
Outlier Detection Engine using IQR and Z-Score methods.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

class OutlierDetector:
    def __init__(self, df: pd.DataFrame):
        self.df = df.select_dtypes(include=[np.number])

    def iqr_outliers(self, factor: float = 1.5) -> Dict[str, Any]:
        results = {}
        for col in self.df.columns:
            q1 = self.df[col].quantile(0.25)
            q3 = self.df[col].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - (factor * iqr)
            upper_bound = q3 + (factor * iqr)
            outliers = self.df[(self.df[col] < lower_bound) | (self.df[col] > upper_bound)][col]
            
            results[col] = {
                "count": len(outliers),
                "percentage": round((len(outliers) / len(self.df)) * 100, 2),
                "recommendation": "Investigate domain validity before removal" if len(outliers) > 0 else "Clean"
            }
        return results