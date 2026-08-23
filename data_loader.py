"""Validated local CSV loading for the dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "iran_events.csv": {"EventCode", "EventRootCode", "GoldsteinScale", "AvgTone", "NumMentions"},
    "gdelt_sentiment.csv": {"title", "url", "seendate", "sentiment", "sentiment_score"},
    "historical_events.csv": {
        "date", "event_count", "avg_goldstein", "avg_tone", "total_mentions", "total_sources", "total_articles"
    },
}


class DataValidationError(ValueError):
    """Raised when a required local data file cannot power a panel safely."""


def load_dashboard_data(data_directory: Path) -> dict[str, pd.DataFrame]:
    """Load dashboard sources, reporting missing files/columns clearly."""
    loaded: dict[str, pd.DataFrame] = {}
    for filename, required in REQUIRED_COLUMNS.items():
        path = data_directory / filename
        if not path.exists():
            raise DataValidationError(f"Missing {filename}. Put it beside app.py or select its folder in the sidebar.")
        try:
            frame = pd.read_csv(path)
        except Exception as exc:
            raise DataValidationError(f"Could not read {filename}: {exc}") from exc
        missing = required.difference(frame.columns)
        if missing:
            raise DataValidationError(f"{filename} is missing: {', '.join(sorted(missing))}")
        if frame.empty:
            raise DataValidationError(f"{filename} has no rows.")
        loaded[filename] = frame
    return loaded
