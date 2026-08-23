"""Transparent, current-risk scoring for the energy supply-chain dashboard.

The model intentionally calculates and explains CURRENT risk. It does not
predict future risk — see the app's "Method" tab for the documented, tested,
and deliberately-not-deployed prediction experiment.
"""

from __future__ import annotations

import pandas as pd


EVENT_WEIGHT = 0.60
SENTIMENT_WEIGHT = 0.40


def risk_category(score: float) -> str:
    """Use the project boundaries: Low <25, Medium <50, High >=50."""
    if score < 25:
        return "LOW"
    if score < 50:
        return "MEDIUM"
    return "HIGH"


def normalise_goldstein(values: pd.Series) -> pd.Series:
    """Map Goldstein's -10 (most conflict) to +10 scale to risk 1..0."""
    return ((10 - pd.to_numeric(values, errors="coerce")) / 20).clip(0, 1)


def normalise_tone(values: pd.Series) -> pd.Series:
    """Map GDELT AvgTone's full -100..+100 range to risk 1..0.

    Correction record: older project scripts clipped AvgTone to +/-10 before
    scaling. This implementation keeps the complete +/-100 range, so values
    below -10 retain their additional risk signal. (This is the fix that
    moved the reference composite score from 57.82 to the corrected 52.49.)
    """
    return ((100 - pd.to_numeric(values, errors="coerce")) / 200).clip(0, 1)


def calculate_current_risk(events: pd.DataFrame, articles: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Return the current 60/40 score and event-level calculation details."""
    event_data = events.copy()
    event_data["goldstein_risk_component"] = normalise_goldstein(event_data["GoldsteinScale"])
    event_data["tone_risk"] = normalise_tone(event_data["AvgTone"])
    event_data["event_risk"] = (
        0.60 * event_data["goldstein_risk_component"]
        + 0.40 * event_data["tone_risk"]
    )
    mentions = pd.to_numeric(event_data["NumMentions"], errors="coerce").fillna(0)
    if mentions.sum() > 0:
        event_score = float((event_data["event_risk"] * mentions).sum() / mentions.sum() * 100)
    else:
        event_score = float(event_data["event_risk"].mean() * 100)

    article_scores = pd.to_numeric(articles["sentiment_score"], errors="coerce")
    sentiment_score = float(((1 - article_scores) / 2).mean() * 100)
    composite = EVENT_WEIGHT * event_score + SENTIMENT_WEIGHT * sentiment_score

    return {
        "event_score": event_score,
        "sentiment_score": sentiment_score,
        "composite_score": composite,
        "category": risk_category(composite),
    }, event_data
