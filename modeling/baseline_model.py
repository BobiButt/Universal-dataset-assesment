"""
Automated Baseline Model Builder
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, mean_squared_error
from typing import Dict, Any

class BaselineModelTrainer:
    def __init__(self, df: pd.DataFrame, target_col: str, task_type: str = "Classification"):
        self.df = df
        self.target_col = target_col
        self.task_type = task_type

    def train_baseline(self) -> Dict[str, Any]:
        X = self.df.drop(columns=[self.target_col])
        y = self.df[self.target_col]
        
        # Ensure only numeric features
        X = X.select_dtypes(include=['number'])

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        if self.task_type == "Classification":
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            acc = accuracy_score(y_test, preds)
            return {"model": "RandomForestClassifier", "metric": "Accuracy", "score": round(acc, 4)}
        else:
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
            return {"model": "RandomForestRegressor", "metric": "RMSE", "score": round(rmse, 4)}