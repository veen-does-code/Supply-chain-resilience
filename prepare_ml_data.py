"""Build the reproducible historical feature set for the offline ML experiment.

This script is deliberately separate from the live Streamlit application.
It evaluates whether the available daily history can forecast next-day risk;
it does not create a production prediction service.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from risk_model import normalise_goldstein, normalise_tone


INPUT_FILE = Path(__file__).with_name("historical_events.csv")
OUTPUT_FILE = Path(__file__).with_name("ml_training_data.csv")
BASE_COLUMNS = ["event_count", "avg_goldstein", "avg_tone", "total_mentions", "total_sources", "total_articles"]


def build_dataset() -> pd.DataFrame:
    """Return dated features known at day-end and next-day training targets."""
    data = pd.read_csv(INPUT_FILE)
    required = {"date", *BASE_COLUMNS}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing historical column(s): {', '.join(sorted(missing))}")
    data["date"] = pd.to_datetime(data["date"])
    data = data.sort_values("date").reset_index(drop=True)

    # Use the current project's corrected normalization, not legacy +/-10 tone clipping.
    data["goldstein_risk"] = normalise_goldstein(data["avg_goldstein"])
    data["tone_risk"] = normalise_tone(data["avg_tone"])
    data["event_risk"] = 100 * (0.60 * data["goldstein_risk"] + 0.40 * data["tone_risk"])
    data["sentiment_risk"] = 100 * data["tone_risk"]
    data["risk_score"] = 0.60 * data["event_risk"] + 0.40 * data["sentiment_risk"]

    for column in BASE_COLUMNS + ["risk_score"]:
        data[f"{column}_lag_1"] = data[column].shift(1)
        data[f"{column}_change_1"] = data[column].diff(1)
        data[f"{column}_mean_3"] = data[column].rolling(3, min_periods=3).mean()

    data["next_day_risk"] = data["risk_score"].shift(-1)
    data["next_day_risk_up"] = (data["next_day_risk"] > data["risk_score"]).astype("Int64")
    features = [c for c in data if c.endswith(("_lag_1", "_change_1", "_mean_3"))]
    return data.dropna(subset=features + ["next_day_risk"]).reset_index(drop=True)


def main() -> None:
    dataset = build_dataset()
    dataset.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {len(dataset)} ML-ready observations to {OUTPUT_FILE.name}")
    print(f"Feature columns: {len([c for c in dataset if c.endswith(('_lag_1', '_change_1', '_mean_3'))])}")


if __name__ == "__main__":
    main()
