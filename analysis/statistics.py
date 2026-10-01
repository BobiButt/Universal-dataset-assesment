"""
Statistical Analysis & Distribution Calculator
"""

import pandas as pd
from typing import Dict, Any

def compute_tabular_statistics(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculates numerical and categorical statistics."""
    num_df = df.select_dtypes(include=['number'])
    cat_df = df.select_dtypes(include=['object', 'category', 'string'])
    
    num_stats = {}
    if not num_df.empty:
        stats = num_df.describe().T
        stats['skewness'] = num_df.skew()
        stats['median'] = num_df.median()
        num_stats = stats[['mean', 'median', 'std', 'min', '50%', 'max', 'skewness']].to_dict(orient='index')

    cat_stats = {}
    for col in cat_df.columns:
        cat_stats[col] = {
            "unique_values": int(cat_df[col].nunique()),
            "top_value": str(cat_df[col].mode()[0]) if not cat_df[col].empty else None,
            "cardinality_ratio": round(cat_df[col].nunique() / len(df), 4)
        }

    return {"numerical_stats": num_stats, "categorical_stats": cat_stats}