"""
Categorical Feature Encoding
"""

import pandas as pd

def encode_categorical_features(df: pd.DataFrame, max_one_hot_cardinality: int = 10) -> pd.DataFrame:
    df_encoded = df.copy()
    cat_cols = df_encoded.select_dtypes(include=['object', 'category', 'string']).columns

    for col in cat_cols:
        cardinality = df_encoded[col].nunique()
        if cardinality <= max_one_hot_cardinality:
            df_encoded = pd.get_dummies(df_encoded, columns=[col], drop_first=True)
        else:
            # Frequency encoding for high cardinality
            freq_map = df_encoded[col].value_counts(normalize=True).to_dict()
            df_encoded[col] = df_encoded[col].map(freq_map)

    return df_encoded