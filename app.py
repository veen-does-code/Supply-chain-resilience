"""Route-based, current-risk dashboard using live GDELT data."""

from __future__ import annotations

from datetime import datetime, timezone
import math

import pandas as pd
import plotly.express as px
import streamlit as st

from digital_twin import create_twin_deck, run_scenario
from live_gdelt import LiveDataError, load_event_data
from reserve_optimizer import optimise_reserve_drawdown
from risk_model import EVENT_WEIGHT, SENTIMENT_WEIGHT
from route_scoring import score_route
from routes import REGIONS, alternative_origins, route_for


st.set_page_config(page_title="Energy Route Risk", page_icon="⚡", layout="wide")


@st.cache_data(ttl=300, show_spinner=False)
def load_latest_events(refresh_nonce: int, offline: bool) -> tuple[pd.DataFrame, dict[str, str]]:
    return load_event_data(force_offline=offline)


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


def route_path_label(start: str, route: list, end: str) -> str:
    return " → ".join([start, *[item.name for item in route], end])


def main() -> None:
    st.title("Energy Supply Route Risk Monitor")
    st.caption("Current GDELT signals for modeled energy-shipping chokepoints — not a forecast.")

    if "refresh_nonce" not in st.session_state:
        st.session_state.refresh_nonce = 0

    with st.sidebar:
        st.header("Route selection")
        start = st.selectbox("Start region", REGIONS, index=0)
        end_choices = [region for region in REGIONS if region != start]
        end = st.selectbox("End region", end_choices, index=end_choices.index("Europe") if "Europe" in end_choices else 0)
        offline = st.toggle("Use offline/cached data", help="Skip live requests and use the latest saved data available on this device.")
        if st.button("Refresh live data", type="primary", disabled=offline):
            st.session_state.refresh_nonce += 1

    route = route_for(start, end)
    route_label = f"{start} → {end}"

    if route is None:
        st.info("This origin–destination pair is not covered by the fixed heuristic. Choose another supported pair; the dashboard will not invent a route.")
        st.stop()

    if not route:
        st.info(
            f"{route_label} is modeled as an open-ocean corridor with no major chokepoint in this simplified "
            "heuristic, so there is nothing to score for this pair yet — this is a documented gap in the "
            "route table, not an error."
        )
        st.stop()

    st.caption("Chokepoint-modeled route, not real-time vessel tracking.")
    with st.expander("How this route and score are modeled"):
        st.write(route_path_label(start, route, end))
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

    result = score_route(route, all_events, event_status, st.session_state.refresh_nonce, offline)

    if result["fallback_notes"]:
        st.info(" ".join(dict.fromkeys(result["fallback_notes"])))
    if result["excluded"]:
        st.caption("Unavailable chokepoints are excluded, not scored as zero: " + " • ".join(result["excluded"]))
    if result["score"] is None:
        st.info("No chokepoint has both usable event and article data for this route yet. The app remains ready to use cached data when a snapshot is available.")
        st.stop()

    successful = result["successful"]
    route_score = result["score"]
    category = result["category"]

    overview_tab, twin_tab, reserve_tab, orchestrator_tab, evidence_tab, trend_tab, method_tab = st.tabs(
        ["Overview", "Digital Twin", "Strategic Reserve", "Procurement Orchestrator", "Evidence", "Trend", "Method"]
    )

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
        st.dataframe(breakdown, use_container_width=True, hide_index=True, column_config={"Risk score": st.column_config.NumberColumn(format="%.2f"), "Event risk (60%)": st.column_config.NumberColumn(format="%.2f"), "VADER risk (40%)": st.column_config.NumberColumn(format="%.2f")})

    with twin_tab:
        st.subheader("Supply Chain Digital Twin")
        st.caption(
            "A geospatial simulation of the modeled energy corridor. Adjust a disruption and the scenario "
            "recalculates immediately from this route's current chokepoint risk signals."
        )
        # Every mapped chokepoint receives a finite current-risk value. When
        # there is no local snapshot, the displayed fallback is the current
        # route average instead of the invalid "NaN" previously shown.
        node_risks = {checkpoint.key: route_score for checkpoint in route}
        node_risks.update({
            item["chokepoint"].key: item["score"]["composite_score"]
            for item in successful
            if math.isfinite(item["score"]["composite_score"])
        })
        control_col, result_col = st.columns([1, 1.4])
        with control_col:
            scenario_choices = ["No disruption", *[checkpoint.name for checkpoint in route]]
            selected_scenario = st.selectbox("Disruption location", scenario_choices)
            affected = next((checkpoint for checkpoint in route if checkpoint.name == selected_scenario), None)
            severity = st.slider(
                "Disruption severity", min_value=0, max_value=100,
                value=0 if affected is None else 50, step=5,
                disabled=affected is None,
                help="0 is normal operations; 100 represents a severe closure-level disruption in this illustrative model.",
            )
            if affected is None:
                st.info("Select a chokepoint to run a what-if scenario.")
                scenario = run_scenario(route_score, node_risks, None, 0)
            else:
                scenario = run_scenario(route_score, node_risks, affected.key, severity)
                st.caption(f"Stress-testing {affected.name} at {severity}% severity.")
        with result_col:
            risk_metric, reliability_metric, delay_metric = st.columns(3)
            risk_metric.metric("Projected route risk", f"{scenario['projected_risk']:.1f} / 100", f"{scenario['risk_change']:+.1f}")
            reliability_metric.metric("Route reliability", f"{scenario['reliability']:.1f}%")
            delay_metric.metric("Illustrative delay", f"{scenario['estimated_delay_days']:.1f} days")
            if affected is not None and severity > 0:
                st.warning(
                    "Scenario output is a planning stress test, not a prediction or a shipping instruction. "
                    "It combines the selected shock with the current risk baseline."
                )
            else:
                st.success("Baseline simulation: no additional disruption applied.")
        st.pydeck_chart(
            create_twin_deck(start, end, route, node_risks, affected.key if affected and severity > 0 else None),
            use_container_width=True,
            height=460,
        )
        legend = pd.DataFrame([
            {"Map marker": "Blue", "Meaning": "Origin"},
            {"Map marker": "Purple", "Meaning": "Destination"},
            {"Map marker": "Green / amber / red", "Meaning": "Current low / medium / high risk chokepoint"},
            {"Map marker": "Red", "Meaning": "Selected disruption location"},
        ])
        with st.expander("Twin scope and assumptions"):
            st.dataframe(legend, hide_index=True, use_container_width=True)
            st.write(
                "The lines show the project's fixed, ordered chokepoint heuristic; they are not exact sailing tracks. "
                "Scenario risk increases by disruption severity, weighted by the selected chokepoint's current "
                "observed risk. Delay and reliability are illustrative planning indicators."
            )

    with reserve_tab:
        st.subheader("Strategic Reserve Optimisation Agent")
        st.caption(
            "Models a conservative reserve drawdown schedule against the current digital-twin stress scenario. "
            "All quantities are expressed as days of normal import demand."
        )
        reserve_controls, reserve_summary = st.columns([1, 1.4])
        with reserve_controls:
            reserve_days = st.slider("Available strategic reserve (days)", 15, 120, 60)
            safety_floor = st.slider("Protected safety floor (days)", 0, reserve_days - 1, min(20, reserve_days - 1))
            horizon_days = st.select_slider("Planning horizon", options=[7, 14, 21, 30], value=14, format_func=lambda days: f"{days} days")
        reserve_schedule, reserve_result = optimise_reserve_drawdown(
            scenario["projected_risk"], reserve_days, safety_floor, horizon_days
        )
        with reserve_summary:
            drawdown_metric, remaining_metric, peak_metric = st.columns(3)
            drawdown_metric.metric("Recommended drawdown", f"{reserve_result['total_drawdown']:.1f} days")
            remaining_metric.metric("Reserve after horizon", f"{reserve_result['reserve_remaining']:.1f} days")
            peak_metric.metric("Peak forecast gap", f"{reserve_result['peak_gap_percent']:.1f}%")
            if reserve_result["uncovered_gap"] > 0:
                st.warning(
                    f"The stress scenario leaves {reserve_result['uncovered_gap']:.1f} demand-days uncovered after "
                    "protecting the selected safety floor. Consider alternative sourcing or a lower reserve floor."
                )
            else:
                st.success("The selected reserve can cover the illustrated gap while preserving the safety floor.")
        reserve_chart = px.line(
            reserve_schedule,
            x="Day",
            y="Reserve remaining (days)",
            markers=True,
            labels={"Reserve remaining (days)": "Reserve remaining (days of demand)"},
        )
        reserve_chart.add_hline(y=safety_floor, line_dash="dash", line_color="#f59e0b", annotation_text="Safety floor")
        reserve_chart.update_layout(margin=dict(l=10, r=10, t=25, b=10), showlegend=False)
        st.plotly_chart(reserve_chart, use_container_width=True)
        st.dataframe(
            reserve_schedule,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Forecast supply gap (% of daily demand)": st.column_config.NumberColumn(format="%.1f%%"),
                "Recommended reserve drawdown (days)": st.column_config.NumberColumn(format="%.2f"),
                "Reserve remaining (days)": st.column_config.NumberColumn(format="%.2f"),
            },
        )
        st.info(
            "This is a planning optimisation, not a supply forecast or an operational order. The gap is a transparent "
            "risk-derived stress profile from the Digital Twin; it does not use inventory, refinery, demand, or contract data."
        )

    with orchestrator_tab:
        st.subheader("Adaptive Procurement Orchestrator")
        st.caption(
            "Ranks alternative sourcing origins to the same destination by modeled current risk. "
            "It does not account for cost, contract terms, lead time, refinery compatibility, or the "
            "physical feasibility of actually switching sources — it is a risk-ranking aid for a "
            "procurement team to act on, not an automated sourcing decision."
        )
        candidates = alternative_origins(end, start)
        if not candidates:
            st.info("No alternative origin region has a modeled route to this destination in the fixed rules table.")
        else:
            rows = [{
                "Origin": start,
                "Modeled route": route_path_label(start, route, end),
                "Risk score": route_score,
                "Category": category,
                "Δ vs current": 0.0,
                "Coverage": f"{len(successful)}/{len(route)}",
                "_current": True,
            }]
            coverage_notes = {start: result["excluded"]}
            with st.spinner("Scoring alternative sourcing origins..."):
                for origin in candidates:
                    alt_route = route_for(origin, end)
                    if not alt_route:
                        continue
                    alt_result = score_route(alt_route, all_events, event_status, st.session_state.refresh_nonce, offline)
                    coverage_notes[origin] = alt_result["excluded"]
                    if alt_result["score"] is None:
                        continue
                    rows.append({
                        "Origin": origin,
                        "Modeled route": route_path_label(origin, alt_route, end),
                        "Risk score": alt_result["score"],
                        "Category": alt_result["category"],
                        "Δ vs current": alt_result["score"] - route_score,
                        "Coverage": f"{len(alt_result['successful'])}/{len(alt_route)}",
                        "_current": False,
                    })

            ranking = pd.DataFrame(rows).sort_values("Risk score").reset_index(drop=True)
            st.dataframe(
                ranking.drop(columns="_current"),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Risk score": st.column_config.NumberColumn(format="%.2f"),
                    "Δ vs current": st.column_config.NumberColumn(format="%+.2f"),
                    "Coverage": st.column_config.TextColumn("Coverage", help="Usable chokepoints / total chokepoints modeled on that route. Matching scores usually mean matching coverage — check here before assuming a tie is a bug."),
                },
            )

            if any(len(notes) > 0 for notes in coverage_notes.values()):
                with st.expander("Why coverage isn't full for every origin"):
                    for origin, notes in coverage_notes.items():
                        if notes:
                            st.caption(f"{origin}: " + " • ".join(notes))
                        else:
                            st.caption(f"{origin}: all modeled chokepoints had usable data.")

            best = ranking.iloc[0]
            if not bool(best["_current"]) and best["Risk score"] < route_score - 0.01:
                st.success(
                    f"Lower modeled risk available: sourcing from **{best['Origin']}** instead of "
                    f"**{start}** would change the modeled route risk from {route_score:.2f} ({category}) "
                    f"to {best['Risk score']:.2f} ({best['Category']})."
                )
            else:
                st.info(f"{start} is already the lowest modeled-risk origin among the alternatives evaluated for this destination.")

            if len(ranking) < len(candidates) + 1:
                st.caption("Some alternative origins were skipped — no usable event/article data was available for their modeled chokepoints in this snapshot.")

    with evidence_tab:
        st.subheader("Source articles used in the score")
        articles = pd.concat([item["articles"].assign(chokepoint=item["chokepoint"].name) for item in successful], ignore_index=True)
        articles["seendate"] = pd.to_datetime(articles["seendate"], errors="coerce")
        st.dataframe(articles[["chokepoint", "seendate", "title", "domain", "sentiment", "sentiment_score", "url"]].sort_values("seendate", ascending=False), use_container_width=True, hide_index=True, column_config={"url": st.column_config.LinkColumn("Source link", display_text="Open article"), "sentiment_score": st.column_config.NumberColumn("VADER score", format="%.3f")})

    with trend_tab:
        trend_history = record_live_observation(route_label, route_score, event_status["fetched_at"])
        st.subheader("Live route-risk observations")
        if len(trend_history) == 1:
            st.caption("First observation for this route in this browser session. Refresh live data to add a comparable observation.")
        trend = px.line(trend_history, x="fetched_at", y="risk_score", markers=True, labels={"fetched_at": "Snapshot time", "risk_score": "Route risk (0–100)"})
        trend.add_hline(y=25, line_dash="dot", line_color="#999999", annotation_text="Medium")
        trend.add_hline(y=50, line_dash="dot", line_color="#999999", annotation_text="High")
        trend.update_layout(yaxis_range=[0, 100], margin=dict(l=10, r=10, t=20, b=10), showlegend=False)
        st.plotly_chart(trend, use_container_width=True)

    with method_tab:
        st.subheader("Score method")
        st.write(f"Event risk: 60% Goldstein component + 40% AvgTone component. Composite: {EVENT_WEIGHT:.0%} Event risk + {SENTIMENT_WEIGHT:.0%} VADER sentiment risk. AvgTone is normalized across its full −100 to +100 range.")
        st.write("The Procurement Orchestrator tab reuses this exact scoring for every alternative origin — it is the same calculation applied to a different modeled route, not a separate model.")
        with st.expander("Experimental ML result — not deployed"):
            st.write("We tested whether historical patterns could predict next-day risk. They did not outperform simple baselines, so prediction is not used in this dashboard.")
            st.dataframe(pd.DataFrame({"Experiment": ["Risk-direction classification", "Next-day risk regression"], "Simple baseline": ["Majority baseline: 55.56% accuracy", "Naive persistence: 1.32 MAE"], "Tested model": ["Logistic Regression: 46.15% accuracy", "Linear Regression: 2.39 MAE"], "Live use": ["Not deployed", "Not deployed"]}), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
