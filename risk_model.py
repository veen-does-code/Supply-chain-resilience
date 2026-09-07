"""Transparent, current-risk scoring for the energy supply-chain dashboard.

The model intentionally calculates and explains CURRENT risk. It does not
predict future risk — see the app's "Method" tab for the documented, tested,
and deliberately-not-deployed prediction experiment.
"""

from __future__ import annotations

import math

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


def _finite_mean(values: pd.Series) -> float | None:
    """Return a finite mean, rather than allowing missing source values to leak as NaN."""
    numeric = pd.to_numeric(values, errors="coerce").replace([float("inf"), float("-inf")], pd.NA).dropna()
    if numeric.empty:
        return None
    value = float(numeric.mean())
    return value if math.isfinite(value) else None


def calculate_current_risk(events: pd.DataFrame, articles: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Return a finite current-risk score and event-level calculation details.

    A source with no valid numeric observations is treated as a neutral 50
    until fresh data arrives. This avoids displaying a mathematically invalid
    result while keeping the other, valid source signal in the calculation.
    """
    event_data = events.copy()
    event_data["goldstein_risk_component"] = normalise_goldstein(event_data["GoldsteinScale"])
    event_data["tone_risk"] = normalise_tone(event_data["AvgTone"])
    event_data["event_risk"] = (
        0.60 * event_data["goldstein_risk_component"]
        + 0.40 * event_data["tone_risk"]
    )
    valid_events = event_data.dropna(subset=["event_risk"]).copy()
    mentions = (
        pd.to_numeric(valid_events["NumMentions"], errors="coerce")
        .replace([float("inf"), float("-inf")], pd.NA)
        .fillna(0)
        .clip(lower=0)
    )
    if not valid_events.empty and mentions.sum() > 0:
        event_score = float((valid_events["event_risk"] * mentions).sum() / mentions.sum() * 100)
    else:
        event_mean = _finite_mean(valid_events["event_risk"] if not valid_events.empty else pd.Series(dtype=float))
        event_score = 50.0 if event_mean is None else event_mean * 100

    article_scores = pd.to_numeric(articles["sentiment_score"], errors="coerce")
    sentiment_mean = _finite_mean((1 - article_scores) / 2)
    sentiment_score = 50.0 if sentiment_mean is None else sentiment_mean * 100
    event_score = 50.0 if not math.isfinite(event_score) else max(0.0, min(100.0, event_score))
    sentiment_score = 50.0 if not math.isfinite(sentiment_score) else max(0.0, min(100.0, sentiment_score))
    composite = EVENT_WEIGHT * event_score + SENTIMENT_WEIGHT * sentiment_score

    # Defend the UI from malformed upstream values even if a future source
    # changes schema or unexpectedly returns infinity.
    composite = 50.0 if not math.isfinite(composite) else max(0.0, min(100.0, composite))

    return {
        "event_score": event_score,
        "sentiment_score": sentiment_score,
        "composite_score": composite,
        "category": risk_category(composite),
    }, event_data
