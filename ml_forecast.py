"""Experimental next-snapshot risk forecast used by the live dashboard.

The models train on the bundled daily history and use only risk-series
features that can also be collected for any live route: latest score, prior
score, one-step change, and a three-observation mean.  This makes the live
input schema explicit and avoids filling unavailable route features with
invented values.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from risk_model import normalise_goldstein, normalise_tone, risk_category


HISTORY_FILE = Path(__file__).with_name("historical_events.csv")
FEATURES = ["risk_score", "risk_score_lag_1", "risk_score_change_1", "risk_score_mean_3"]
MINIMUM_LIVE_OBSERVATIONS = 3


def _historical_risk_series() -> pd.DataFrame:
    """Build the corrected composite-risk series used for model training."""
    data = pd.read_csv(HISTORY_FILE)
    data["date"] = pd.to_datetime(data["date"])
    data = data.sort_values("date").reset_index(drop=True)
    goldstein_risk = normalise_goldstein(data["avg_goldstein"])
    tone_risk = normalise_tone(data["avg_tone"])
    event_risk = 100 * (0.60 * goldstein_risk + 0.40 * tone_risk)
    data["risk_score"] = 0.60 * event_risk + 0.40 * (100 * tone_risk)
    data["risk_score_lag_1"] = data["risk_score"].shift(1)
    data["risk_score_change_1"] = data["risk_score"].diff(1)
    data["risk_score_mean_3"] = data["risk_score"].rolling(3, min_periods=3).mean()
    data["next_risk"] = data["risk_score"].shift(-1)
    data["next_risk_up"] = (data["next_risk"] > data["risk_score"]).astype("Int64")
    return data.dropna(subset=FEATURES + ["next_risk"]).reset_index(drop=True)


def forecast_next_snapshot(history: pd.DataFrame) -> dict | None:
    """Forecast the next route observation, or return None until history is sufficient.

    `history` must contain the current route's time-ordered `risk_score`.
    The function is deterministic and trains only on local bundled data.
    """
    if len(history) < MINIMUM_LIVE_OBSERVATIONS:
        return None

    scores = pd.to_numeric(history["risk_score"], errors="coerce").dropna()
    if len(scores) < MINIMUM_LIVE_OBSERVATIONS:
        return None
    scores = scores.iloc[-MINIMUM_LIVE_OBSERVATIONS:]
    live_features = pd.DataFrame([{
        "risk_score": scores.iloc[-1],
        "risk_score_lag_1": scores.iloc[-2],
        "risk_score_change_1": scores.iloc[-1] - scores.iloc[-2],
        "risk_score_mean_3": scores.mean(),
    }])

    training = _historical_risk_series()
    x_train = training[FEATURES]

    regressor = Pipeline([("scale", StandardScaler()), ("model", LinearRegression())])
    regressor.fit(x_train, training["next_risk"])
    predicted_score = float(regressor.predict(live_features)[0])
    predicted_score = max(0.0, min(100.0, predicted_score))

    classifier = Pipeline([("scale", StandardScaler()), ("model", LogisticRegression(max_iter=2_000, random_state=42))])
    classifier.fit(x_train, training["next_risk_up"].astype(int))
    probability_up = float(classifier.predict_proba(live_features)[0, list(classifier.classes_).index(1)])

    return {
        "predicted_score": predicted_score,
        "predicted_category": risk_category(predicted_score),
        "change_from_current": predicted_score - float(scores.iloc[-1]),
        "probability_up": probability_up,
        "training_observations": len(training),
        "live_observations": len(history),
    }
