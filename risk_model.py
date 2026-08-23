"""Transparent, current-risk scoring for the energy supply-chain dashboard.

The model intentionally calculates and explains current risk.  It does not
predict future risk.
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
    scaling.  This implementation keeps the complete +/-100 range, so values
    below -10 retain their additional risk signal.
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


def calculate_historical_risk(history: pd.DataFrame) -> pd.DataFrame:
    """Create a comparable daily event/tone trend from historical event data.

    Historical article-level VADER scores are unavailable.  The trend therefore
    uses AvgTone as its documented daily sentiment proxy, rather than claiming
    it is the live VADER component.
    """
    result = history.copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    result = result.dropna(subset=["date"]).sort_values("date")
    result["goldstein_risk_component"] = normalise_goldstein(result["avg_goldstein"])
    result["tone_risk"] = normalise_tone(result["avg_tone"])
    result["event_risk"] = (
        0.60 * result["goldstein_risk_component"] + 0.40 * result["tone_risk"]
    ) * 100
    result["tone_sentiment_proxy"] = result["tone_risk"] * 100
    result["risk_score"] = (
        EVENT_WEIGHT * result["event_risk"]
        + SENTIMENT_WEIGHT * result["tone_sentiment_proxy"]
    )
    return result
