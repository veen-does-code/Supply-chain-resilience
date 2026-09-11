"""Evaluate offline next-day risk baselines and ML models reproducibly.

The output is evidence for the project's Method section. It intentionally
does not write a deployed model or connect predictions to app.py.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import accuracy_score, mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from prepare_ml_data import build_dataset


RESULTS_FILE = Path(__file__).with_name("ml_experiment_results.csv")
PREDICTIONS_FILE = Path(__file__).with_name("ml_experiment_predictions.csv")
TEST_FRACTION = 0.20


def feature_columns(data: pd.DataFrame) -> list[str]:
    return [c for c in data if c.endswith(("_lag_1", "_change_1", "_mean_3"))]


def main() -> None:
    data = build_dataset()
    features = feature_columns(data)
    split_index = int(len(data) * (1 - TEST_FRACTION))
    if split_index < 1 or len(data) - split_index < 2:
        raise ValueError("Not enough observations for a chronological train/test experiment.")
    train, test = data.iloc[:split_index].copy(), data.iloc[split_index:].copy()
    x_train, x_test = train[features], test[features]

    # Classification: will tomorrow's composite risk be higher than today's?
    y_direction_train = train["next_day_risk_up"].astype(int)
    y_direction_test = test["next_day_risk_up"].astype(int)
    majority_class = int(y_direction_train.mode().iloc[0])
    majority_accuracy = accuracy_score(y_direction_test, [majority_class] * len(test))
    classifier = Pipeline([("scale", StandardScaler()), ("model", LogisticRegression(max_iter=2000, random_state=42))])
    classifier.fit(x_train, y_direction_train)
    logistic_prediction = classifier.predict(x_test)
    logistic_accuracy = accuracy_score(y_direction_test, logistic_prediction)

    # Regression: predict the next available historical day's composite score.
    y_risk_train, y_risk_test = train["next_day_risk"], test["next_day_risk"]
    persistence_prediction = test["risk_score"]
    persistence_mae = mean_absolute_error(y_risk_test, persistence_prediction)
    regressor = Pipeline([("scale", StandardScaler()), ("model", LinearRegression())])
    regressor.fit(x_train, y_risk_train)
    linear_prediction = regressor.predict(x_test)
    linear_mae = mean_absolute_error(y_risk_test, linear_prediction)

    results = pd.DataFrame([
        {"task": "Risk-direction classification", "baseline": "Majority class", "baseline_metric": "accuracy", "baseline_score": majority_accuracy, "model": "Logistic Regression", "model_metric": "accuracy", "model_score": logistic_accuracy, "model_beats_baseline": logistic_accuracy > majority_accuracy},
        {"task": "Next-day risk regression", "baseline": "Naive persistence", "baseline_metric": "MAE", "baseline_score": persistence_mae, "model": "Linear Regression", "model_metric": "MAE", "model_score": linear_mae, "model_beats_baseline": linear_mae < persistence_mae},
    ])
    results.to_csv(RESULTS_FILE, index=False)
    predictions = test[["date", "risk_score", "next_day_risk", "next_day_risk_up"]].copy()
    predictions["majority_direction_prediction"] = majority_class
    predictions["logistic_direction_prediction"] = logistic_prediction
    predictions["persistence_risk_prediction"] = persistence_prediction.to_numpy()
    predictions["linear_risk_prediction"] = linear_prediction
    predictions.to_csv(PREDICTIONS_FILE, index=False)

    print(f"Chronological split: {len(train)} train / {len(test)} test observations")
    print(results[["task", "baseline_score", "model_score", "model_beats_baseline"]].to_string(index=False))
    print(f"Saved results to {RESULTS_FILE.name} and predictions to {PREDICTIONS_FILE.name}")


if __name__ == "__main__":
    main()
