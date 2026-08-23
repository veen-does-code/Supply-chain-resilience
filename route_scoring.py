"""Shared per-route scoring, used by both the primary route view and the
Adaptive Procurement Orchestrator's alternative-source ranking.

Factored out so a route is scored exactly the same way whether it's the
route the user picked or an alternative being compared against it -- no
duplicated logic to drift out of sync.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from live_gdelt import LiveDataError, events_for_chokepoint, load_articles
from risk_model import calculate_current_risk, risk_category
from routes import CHOKEPOINTS, Chokepoint


@st.cache_data(ttl=300, show_spinner=False)
def _cached_articles(chokepoint_key: str, refresh_nonce: int, offline: bool) -> tuple[pd.DataFrame, dict[str, str]]:
    return load_articles(CHOKEPOINTS[chokepoint_key], force_offline=offline)


def score_route(
    route: list[Chokepoint],
    all_events: pd.DataFrame,
    event_status: dict[str, str],
    refresh_nonce: int,
    offline: bool,
) -> dict:
    """Score every chokepoint on a route and combine into a route-level result.

    Returns a dict with:
      score          float | None -- route composite risk, or None if no
                                      chokepoint on the route had usable data
      category       str | None
      successful     list of per-chokepoint result dicts
      excluded       list[str] of human-readable exclusion reasons
      fallback_notes list[str] of any non-live data source notices

    A chokepoint with no usable data is excluded from the average, never
    scored as zero -- consistent with how the primary route view already
    behaves.
    """
    successful: list[dict] = []
    excluded: list[str] = []
    fallback_notes: list[str] = []

    for chokepoint in route:
        events = events_for_chokepoint(all_events, chokepoint, event_status)
        if events.empty:
            excluded.append(f"{chokepoint.name}: no matching events in this snapshot")
            continue
        try:
            articles, article_status = _cached_articles(chokepoint.key, refresh_nonce, offline)
        except LiveDataError:
            excluded.append(f"{chokepoint.name}: no saved article data is available")
            continue
        if articles.empty:
            excluded.append(f"{chokepoint.name}: no recent route-relevant articles")
            continue
        if article_status["source"] != "live":
            fallback_notes.append(article_status["message"])
        score, scored_events = calculate_current_risk(events, articles)
        successful.append({"chokepoint": chokepoint, "score": score, "events": scored_events, "articles": articles})

    if not successful:
        return {"score": None, "category": None, "successful": [], "excluded": excluded, "fallback_notes": fallback_notes}

    route_score = sum(item["score"]["composite_score"] for item in successful) / len(successful)
    return {
        "score": route_score,
        "category": risk_category(route_score),
        "successful": successful,
        "excluded": excluded,
        "fallback_notes": fallback_notes,
    }
