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
      score          float | None -- observed route composite risk, or None
                                      if no chokepoint has any usable data
      category       str | None
      successful     list of per-chokepoint result dicts
      excluded       list[str] of human-readable exclusion reasons
      fallback_notes list[str] of any non-live data source notices

    A chokepoint can be scored from events or articles alone; the missing
    component is neutralised by calculate_current_risk(). A chokepoint with
    neither source is excluded, never scored as zero. `is_complete` tells
    callers whether a route is safe to compare with other full-coverage routes.
    """
    successful: list[dict] = []
    excluded: list[str] = []
    fallback_notes: list[str] = []

    for chokepoint in route:
        events = events_for_chokepoint(all_events, chokepoint, event_status)
        try:
            articles, article_status = _cached_articles(chokepoint.key, refresh_nonce, offline)
        except LiveDataError:
            articles = pd.DataFrame(columns=["sentiment_score"])
            article_status = None

        if events.empty and articles.empty:
            excluded.append(f"{chokepoint.name}: no current event or article data")
            continue
        if article_status is not None and article_status["source"] != "live":
            fallback_notes.append(article_status["message"])

        score, scored_events = calculate_current_risk(events, articles)
        if events.empty:
            data_basis = "Article signal + neutral event component"
        elif articles.empty:
            data_basis = "Event signal + neutral article component"
        else:
            data_basis = "Event + article signals"
        successful.append({
            "chokepoint": chokepoint,
            "score": score,
            "events": scored_events,
            "articles": articles,
            "data_basis": data_basis,
        })

    if not successful:
        return {
            "score": None, "category": None, "successful": [], "excluded": excluded,
            "fallback_notes": fallback_notes, "is_complete": False,
        }

    route_score = sum(item["score"]["composite_score"] for item in successful) / len(successful)
    return {
        "score": route_score,
        "category": risk_category(route_score),
        "successful": successful,
        "excluded": excluded,
        "fallback_notes": fallback_notes,
        "is_complete": len(successful) == len(route),
    }
