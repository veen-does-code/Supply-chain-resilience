"""Route-based, current-risk dashboard using live GDELT data."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import streamlit as st

from live_gdelt import LiveDataError, filter_events, load_articles, load_event_data
from risk_model import EVENT_WEIGHT, SENTIMENT_WEIGHT, calculate_current_risk, risk_category
from routes import CHOKEPOINTS, REGIONS, route_for, valid_destinations


st.set_page_config(page_title="Energy Route Risk", page_icon="⚡", layout="wide")

def apply_custom_css():
    st.markdown("""
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        [data-testid="stMetricValue"] {
            font-size: 2.2rem;
            font-weight: 700;
        }
        [data-testid="stMetricLabel"] {
            font-size: 1.1rem;
            color: #6c757d;
        }
        </style>
    """, unsafe_allow_html=True)



@st.cache_data(ttl=300, show_spinner=False)
def load_latest_events(refresh_nonce: int, offline: bool) -> tuple[pd.DataFrame, dict[str, str]]:
    return load_event_data(force_offline=offline)


@st.cache_data(ttl=300, show_spinner=False)
def load_route_articles(chokepoint_key: str, refresh_nonce: int, offline: bool) -> tuple[pd.DataFrame, dict[str, str]]:
    return load_articles(CHOKEPOINTS[chokepoint_key], force_offline=offline)


def friendly_time(value: str) -> str:
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (TypeError, ValueError):
        return "an unknown time"


def record_live_observation(route_label: str, score: float, timestamp: str) -> pd.DataFrame:
    """Keep a route-aware trend only for distinct data snapshots in this session."""
    history = st.session_state.setdefault("live_route_history", [])
    key = f"{route_label}|{timestamp}"
    if not any(item["key"] == key for item in history):
        history.append({"key": key, "route": route_label, "fetched_at": timestamp, "risk_score": score})
    return pd.DataFrame([item for item in history if item["route"] == route_label])


def risk_status(category: str) -> None:
    message = f"Risk level: {category}"
    if category == "HIGH":
        st.error(message)
    elif category == "MEDIUM":
        st.warning(message)
    else:
        st.success(message)


def main() -> None:
    apply_custom_css()
    st.title("⚡ Energy Supply Route Risk Monitor")
    st.caption("Current GDELT signals for modeled energy-shipping chokepoints — not a forecast.")

    if "refresh_nonce" not in st.session_state:
        st.session_state.refresh_nonce = 0

    with st.sidebar:
        st.header("Route selection")
        start = st.selectbox("Start region", REGIONS, index=0)
        
        # Filter end regions to only show valid destinations for the chosen start region
        valid_ends = valid_destinations(start)
        end_choices = valid_ends if valid_ends else [region for region in REGIONS if region != start]
        
        end = st.selectbox("End region", end_choices, index=end_choices.index("Europe") if "Europe" in end_choices else 0)
        offline = st.toggle("Use offline/cached data", help="Skip live requests and use the latest saved data available on this device.")
        if st.button("Refresh live data", type="primary", disabled=offline):
            st.session_state.refresh_nonce += 1

    route = route_for(start, end)
    route_label = f"{start} → {end}"
    if not route:
        st.info("This origin–destination pair is not covered by the fixed heuristic. Choose another supported pair; the dashboard will not invent a route.")
        st.stop()

    st.caption("Chokepoint-modeled route, not real-time vessel tracking.")
    with st.expander("How this route and score are modeled"):
        st.write(" → ".join([start, *[item.name for item in route], end]))
        st.write("The fixed chokepoint rules are an illustrative shortcut, not precise geospatial routing. Each usable chokepoint score combines 60% GDELT Event risk and 40% VADER article-sentiment risk; the route score is their equal-weight average.")

    try:
        with st.spinner("Checking the latest data source..."):
            all_events, event_status = load_latest_events(st.session_state.refresh_nonce, offline)
    except LiveDataError:
        st.info("Live data is unavailable and no saved snapshot is available yet. Try again on a working network, or use the bundled snapshot for a Hormuz route.")
        st.stop()

    if event_status["source"] == "live":
        st.caption(f"Live data loaded • {friendly_time(event_status['fetched_at'])}")
    else:
        st.info(f"{event_status['message']} Saved {friendly_time(event_status['fetched_at'])}.")

    successful: list[dict] = []
    excluded: list[str] = []
    fallback_notes: list[str] = []
    for chokepoint in route:
        events = filter_events(all_events, chokepoint)
        if events.empty:
            excluded.append(f"{chokepoint.name}: no matching events in this snapshot")
            continue
        try:
            articles, article_status = load_route_articles(chokepoint.key, st.session_state.refresh_nonce, offline)
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

    if fallback_notes:
        st.info(" ".join(dict.fromkeys(fallback_notes)))
    if excluded:
        st.caption("Unavailable chokepoints are excluded, not scored as zero: " + " • ".join(excluded))
    if not successful:
        st.info("No chokepoint has both usable event and article data for this route yet. The app remains ready to use cached data when a snapshot is available.")
        st.stop()

    route_score = sum(item["score"]["composite_score"] for item in successful) / len(successful)
    category = risk_category(route_score)
    overview_tab, evidence_tab, trend_tab, method_tab = st.tabs(["Overview", "Evidence", "Trend", "Method"])

    with overview_tab:
        st.subheader(route_label)
        score_column, components_column, coverage_column = st.columns(3)
        score_column.metric("Route risk", f"{route_score:.2f} / 100")
        with components_column:
            st.metric("Usable chokepoints", f"{len(successful)} / {len(route)}")
            st.caption("Equal route weights")
        with coverage_column:
            average_event = sum(item["score"]["event_score"] for item in successful) / len(successful)
            average_sentiment = sum(item["score"]["sentiment_score"] for item in successful) / len(successful)
            st.metric("Average components", f"{average_event:.1f} / {average_sentiment:.1f}")
            st.caption("Event / VADER")
        risk_status(category)
        st.subheader("Per-chokepoint breakdown")
        breakdown = pd.DataFrame([
            {"Chokepoint": item["chokepoint"].name, "Risk score": item["score"]["composite_score"], "Category": item["score"]["category"], "Event risk (60%)": item["score"]["event_score"], "VADER risk (40%)": item["score"]["sentiment_score"], "Events": len(item["events"]), "Articles": len(item["articles"])}
            for item in successful
        ])
        styled_breakdown = breakdown.style.background_gradient(
            cmap="RdYlGn_r", subset=["Risk score", "Event risk (60%)", "VADER risk (40%)"], vmin=0, vmax=100
        ).format({
            "Risk score": "{:.2f}",
            "Event risk (60%)": "{:.2f}",
            "VADER risk (40%)": "{:.2f}"
        })
        st.dataframe(styled_breakdown, width="stretch", hide_index=True)

    with evidence_tab:
        st.subheader("Source articles used in the score")
        articles = pd.concat([item["articles"].assign(chokepoint=item["chokepoint"].name) for item in successful], ignore_index=True)
        articles["seendate"] = pd.to_datetime(articles["seendate"], errors="coerce")
        st.dataframe(articles[["chokepoint", "seendate", "title", "domain", "sentiment", "sentiment_score", "url"]].sort_values("seendate", ascending=False), width="stretch", hide_index=True, column_config={"url": st.column_config.LinkColumn("Source link", display_text="Open article"), "sentiment_score": st.column_config.NumberColumn("VADER score", format="%.3f")})

    with trend_tab:
        trend_history = record_live_observation(route_label, route_score, event_status["fetched_at"])
        st.subheader("Live route-risk observations")
        if len(trend_history) == 1:
            st.caption("First observation for this route in this browser session. Refresh live data to add a comparable observation.")
            trend = px.scatter(trend_history, x="fetched_at", y="risk_score", labels={"fetched_at": "Snapshot time", "risk_score": "Route risk (0–100)"})
            trend.update_traces(marker=dict(size=10))
        else:
            trend = px.line(trend_history, x="fetched_at", y="risk_score", markers=True, labels={"fetched_at": "Snapshot time", "risk_score": "Route risk (0–100)"})
        trend.add_hline(y=25, line_dash="dot", line_color="#999999", annotation_text="Medium")
        trend.add_hline(y=50, line_dash="dot", line_color="#999999", annotation_text="High")
        trend.update_layout(yaxis_range=[0, 100], margin=dict(l=10, r=10, t=20, b=10), showlegend=False)
        st.plotly_chart(trend, width="stretch")

    with method_tab:
        st.subheader("Score method")
        st.write(f"Event risk: 60% Goldstein component + 40% AvgTone component. Composite: {EVENT_WEIGHT:.0%} Event risk + {SENTIMENT_WEIGHT:.0%} VADER sentiment risk. AvgTone is normalized across its full −100 to +100 range.")
        with st.expander("Experimental ML result — not deployed"):
            st.write("We tested whether historical patterns could predict next-day risk. They did not outperform simple baselines, so prediction is not used in this dashboard.")
            st.dataframe(pd.DataFrame({"Experiment": ["Risk-direction classification", "Next-day risk regression"], "Simple baseline": ["Majority baseline: 55.56% accuracy", "Naive persistence: 1.32 MAE"], "Tested model": ["Logistic Regression: 46.15% accuracy", "Linear Regression: 2.39 MAE"], "Live use": ["Not deployed", "Not deployed"]}), width="stretch", hide_index=True)


if __name__ == "__main__":
    main()
