"""
Data Cleaning Engine
Performs explicit transformations: missing value imputations and duplicate removal.
"""

import pandas as pd
from typing import Any, Dict, List, Optional, Tuple

class DataCleaner:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def remove_duplicates(self) -> Tuple[pd.DataFrame, int]:
        initial_len = len(self.df)
        self.df = self.df.drop_duplicates()
        removed = initial_len - len(self.df)
        return self.df, removed

    def handle_missing_values(self, numerical_strategy: str = "median", categorical_strategy: str = "mode") -> pd.DataFrame:
        for col in self.df.columns:
            if self.df[col].isnull().sum() > 0:
                if pd.api.types.is_numeric_dtype(self.df[col]):
                    if numerical_strategy == "median":
                        self.df[col] = self.df[col].fillna(self.df[col].median())
                    elif numerical_strategy == "mean":
                        self.df[col] = self.df[col].fillna(self.df[col].mean())
                else:
                    if categorical_strategy == "mode":
                        mode_val = self.df[col].mode()[0] if not self.df[col].mode().empty else "Unknown"
                        self.df[col] = self.df[col].fillna(mode_val)
        return self.df

    @staticmethod
    def _profile(df: pd.DataFrame) -> Dict[str, int]:
        """Small snapshot used to show before/after results in the fixed report."""
        return {
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "missing_cells": int(df.isnull().sum().sum()),
            "duplicate_rows": int(df.duplicated().sum()),
            "empty_rows": int(df.isnull().all(axis=1).sum()),
            "empty_columns": int(df.isnull().all(axis=0).sum()),
        }

    def optimize_for_training(
        self,
        *,
        target: Optional[str] = None,
        fix_missing: bool = True,
        drop_duplicates: bool = True,
        drop_empty_columns: bool = True,
        drop_empty_rows: bool = True,
        missing_threshold: Optional[float] = None,
        numerical_strategy: str = "median",
        categorical_strategy: str = "mode",
        coerce_numeric: bool = True,
        strip_column_names: bool = True,
        strip_strings: bool = True,
        encode_categorical: bool = False,
        max_one_hot_cardinality: int = 10,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Produce a training-ready copy of the dataset and a change report.

        Every transformation is optional and recorded so the generated
        "fixed report" can explain exactly what happened to the data.
        """
        df = self.df.copy()
        actions: List[Dict[str, Any]] = []
        before = self._profile(df)

        if strip_column_names:
            original_columns = list(df.columns)
            df.columns = [str(column).strip() for column in df.columns]
            renamed = sum(1 for old, new in zip(original_columns, df.columns) if str(old) != new)
            if renamed:
                actions.append({
                    "step": "Normalize column names",
                    "detail": f"Trimmed whitespace from {renamed} column name(s).",
                    "count": renamed,
                })

        columns_dropped: List[str] = []
        if drop_empty_columns:
            empty_columns = [column for column in df.columns if df[column].isnull().all()]
            if empty_columns:
                df = df.drop(columns=empty_columns)
                columns_dropped.extend(empty_columns)
                actions.append({
                    "step": "Drop empty columns",
                    "detail": f"Removed {len(empty_columns)} fully-empty column(s): {', '.join(empty_columns)}.",
                    "count": len(empty_columns),
                })

        if missing_threshold is not None:
            high_missing = [
                column for column in df.columns
                if column != target and df[column].isnull().mean() > missing_threshold
            ]
            if high_missing:
                df = df.drop(columns=high_missing)
                columns_dropped.extend(high_missing)
                actions.append({
                    "step": "Drop high-missing columns",
                    "detail": f"Removed {len(high_missing)} column(s) missing more than {missing_threshold:.0%}.",
                    "count": len(high_missing),
                })


        rows_removed_empty = 0
        if drop_empty_rows:
            empty_row_mask = df.isnull().all(axis=1)
            rows_removed_empty = int(empty_row_mask.sum())
            if rows_removed_empty:
                df = df.loc[~empty_row_mask]
                actions.append({
                    "step": "Drop empty rows",
                    "detail": f"Removed {rows_removed_empty} fully-empty row(s).",
                    "count": rows_removed_empty,
                })

        duplicates_removed = 0
        if drop_duplicates:
            duplicates_removed = int(df.duplicated().sum())
            if duplicates_removed:
                df = df.drop_duplicates()
                actions.append({
                    "step": "Remove duplicate rows",
                    "detail": f"Removed {duplicates_removed} exact duplicate row(s).",
                    "count": duplicates_removed,
                })

        if strip_strings:
            text_columns = df.select_dtypes(include=["object", "string"]).columns
            stripped_total = 0
            for column in text_columns:
                normalized = df[column].map(lambda value: value.strip() if isinstance(value, str) else value)
                changed = int((normalized.ne(df[column])).sum())
                if changed:
                    df[column] = normalized
                    stripped_total += changed
            if stripped_total:
                actions.append({
                    "step": "Trim whitespace in text values",
                    "detail": f"Normalized {stripped_total} text value(s) with stray whitespace.",
                    "count": stripped_total,
                })

        dtypes_coerced: Dict[str, str] = {}
        if coerce_numeric:
            for column in df.select_dtypes(include=["object", "string"]).columns:
                if column == target:
                    continue
                series = df[column]
                populated = int(series.notna().sum())
                if populated == 0:
                    continue
                converted = pd.to_numeric(series, errors="coerce")
                # Only accept if every populated value parsed as a number.
                if int(converted.notna().sum()) == populated:
                    df[column] = converted
                    dtypes_coerced[column] = str(converted.dtype)
            if dtypes_coerced:
                actions.append({
                    "step": "Fix column data types",
                    "detail": f"Converted {len(dtypes_coerced)} text column(s) to numeric.",
                    "count": len(dtypes_coerced),
                })

        imputed_cells: Dict[str, int] = {}
        if fix_missing:
            for column in df.columns:
                if column == target:
                    continue
                missing_count = int(df[column].isnull().sum())
                if missing_count == 0:
                    continue
                if pd.api.types.is_numeric_dtype(df[column]):
                    if numerical_strategy == "mean":
                        fill_value = df[column].mean()
                    elif numerical_strategy == "zero":
                        fill_value = 0
                    else:
                        fill_value = df[column].median()
                    if pd.isna(fill_value):
                        fill_value = 0
                else:
                    modes = df[column].mode()
                    fill_value = modes.iloc[0] if not modes.empty else "Unknown"
                df[column] = df[column].fillna(fill_value)
                imputed_cells[column] = missing_count
            if imputed_cells:
                total_imputed = int(sum(imputed_cells.values()))
                actions.append({
                    "step": "Fill missing values",
                    "detail": f"Imputed {total_imputed} missing cell(s) across {len(imputed_cells)} column(s).",
                    "count": total_imputed,
                })

        encoded = False
        columns_added: List[str] = []
        if encode_categorical:
            from preprocessing.encode_data import encode_categorical_features

            columns_before = set(df.columns)
            if target is not None and target in df.columns:
                target_series = df[target]
                features = encode_categorical_features(df.drop(columns=[target]), max_one_hot_cardinality)
                df = features.copy()
                df[target] = target_series
            else:
                df = encode_categorical_features(df, max_one_hot_cardinality)
            columns_added = [column for column in df.columns if column not in columns_before]
            encoded = True
            actions.append({
                "step": "Encode categorical features",
                "detail": f"Encoded categorical features into {len(columns_added)} numeric column(s).",
                "count": len(columns_added),
            })

        df = df.reset_index(drop=True)

        if not actions:
            actions.append({
                "step": "No changes required",
                "detail": "The dataset already satisfied every selected check.",
                "count": 0,
            })

        after = self._profile(df)
        report: Dict[str, Any] = {
            "status": "ok",
            "options": {
                "target": target,
                "fix_missing": fix_missing,
                "drop_duplicates": drop_duplicates,
                "drop_empty_columns": drop_empty_columns,
                "drop_empty_rows": drop_empty_rows,
                "missing_threshold": missing_threshold,
                "numerical_strategy": numerical_strategy,
                "categorical_strategy": categorical_strategy,
                "coerce_numeric": coerce_numeric,
                "encode_categorical": encode_categorical,
            },
            "before": before,
            "after": after,
            "actions": actions,
            "columns_dropped": columns_dropped,
            "columns_added": columns_added,
            "duplicates_removed": duplicates_removed,
            "rows_removed_empty": rows_removed_empty,
            "imputed_cells": imputed_cells,
            "total_imputed": int(sum(imputed_cells.values())),
            "dtypes_coerced": dtypes_coerced,
            "encoded": encoded,
        }
        return df, report


def optimize_dataframe(df: pd.DataFrame, **options: Any) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Convenience wrapper around :meth:`DataCleaner.optimize_for_training`."""
    return DataCleaner(df).optimize_for_training(**options)

