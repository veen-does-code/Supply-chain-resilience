"""Streamlit dashboard for current Iran / Strait of Hormuz supply-chain risk."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from data_loader import DataValidationError, load_dashboard_data
from risk_model import EVENT_WEIGHT, SENTIMENT_WEIGHT, calculate_current_risk, calculate_historical_risk


st.set_page_config(page_title="India Energy Supply Risk", page_icon="⚡", layout="wide")


@st.cache_data(show_spinner=False)
def load_data(directory: str) -> dict[str, pd.DataFrame]:
    return load_dashboard_data(Path(directory))


def score_colour(category: str) -> str:
    return {"LOW": "#1f8a5b", "MEDIUM": "#d98000", "HIGH": "#c74343"}[category]


def explanation(score: dict, events: pd.DataFrame, articles: pd.DataFrame) -> str:
    avg_goldstein = pd.to_numeric(events["GoldsteinScale"], errors="coerce").mean()
    avg_tone = pd.to_numeric(events["AvgTone"], errors="coerce").mean()
    negative_share = (articles["sentiment"].astype(str).str.lower() == "negative").mean()
    goldstein_phrase = "conflict-oriented" if avg_goldstein < 0 else "less conflict-oriented"
    tone_phrase = "negative" if avg_tone < 0 else "non-negative"
    return (
        f"Current risk is {score['category']} at {score['composite_score']:.2f}/100. "
        f"The event signal contributes {score['event_score']:.2f}/100 and VADER article sentiment contributes "
        f"{score['sentiment_score']:.2f}/100. Across {len(events):,} Iran-related GDELT events, the average "
        f"Goldstein score is {avg_goldstein:.2f} ({goldstein_phrase}) and average media tone is {avg_tone:.2f} "
        f"({tone_phrase}); {negative_share:.0%} of the {len(articles)} source articles are labelled negative."
    )


def main() -> None:
    st.title("India Energy Supply Chain Risk Monitor")
    st.caption("Current Iran / Strait of Hormuz disruption context • Interpretable 60/40 composite • Not a forecast")

    with st.sidebar:
        st.header("Data")
        default_directory = str(Path(__file__).resolve().parent)
        data_directory = st.text_input("Folder containing the CSV files", value=default_directory)
        st.caption("The dashboard only reads local CSVs; it does not fetch live GDELT data.")

    try:
        data = load_data(data_directory)
    except DataValidationError as exc:
        st.error(str(exc))
        st.info("Required files: iran_events.csv, gdelt_sentiment.csv, historical_events.csv")
        st.stop()

    score, event_data = calculate_current_risk(data["iran_events.csv"], data["gdelt_sentiment.csv"])
    events = data["iran_events.csv"]
    articles = data["gdelt_sentiment.csv"].copy()
    history = calculate_historical_risk(data["historical_events.csv"])

    st.markdown("### Current composite risk")
    headline, event_metric, sentiment_metric, context_metric = st.columns([1.35, 1, 1, 1])
    with headline:
        st.markdown(
            f"<div style='padding: 1rem; border-left: 8px solid {score_colour(score['category'])}; background: #f7f8fa;'>"
            f"<div style='font-size: .9rem;'>CURRENT RISK</div><div style='font-size: 3rem; font-weight: 700;'>"
            f"{score['composite_score']:.2f}<span style='font-size: 1.1rem;'> / 100</span></div>"
            f"<div style='font-weight: 700; color: {score_colour(score['category'])};'>{score['category']}</div></div>",
            unsafe_allow_html=True,
        )
    event_metric.metric("GDELT event risk", f"{score['event_score']:.2f}", "60% weight")
    sentiment_metric.metric("VADER sentiment risk", f"{score['sentiment_score']:.2f}", "40% weight")
    context_metric.metric("Iran-related events", f"{len(events):,}", "current event file")

    st.info(explanation(score, events, articles))

    left, right = st.columns([1.7, 1])
    with left:
        st.subheader("Historical risk trend")
        recent = history[history["date"] >= history["date"].max() - pd.Timedelta(days=60)]
        trend = px.line(
            recent,
            x="date",
            y=["risk_score", "event_risk", "tone_sentiment_proxy"],
            labels={"value": "Risk score (0–100)", "variable": "Series", "date": "Date"},
            color_discrete_map={"risk_score": "#c74343", "event_risk": "#2467a8", "tone_sentiment_proxy": "#8c5bb3"},
        )
        trend.update_traces(mode="lines+markers")
        trend.add_hline(y=25, line_dash="dot", line_color="#d98000", annotation_text="Medium threshold")
        trend.add_hline(y=50, line_dash="dot", line_color="#c74343", annotation_text="High threshold")
        trend.update_layout(legend_title_text="", yaxis_range=[0, 100], margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(trend, use_container_width=True)
        st.caption("Historical trend uses the available daily GDELT event aggregates. Its ‘sentiment proxy’ is AvgTone; it is not historical VADER article sentiment.")
    with right:
        st.subheader("How the score is built")
        contribution = pd.DataFrame({
            "Component": ["GDELT event risk", "VADER sentiment risk"],
            "Weighted contribution": [EVENT_WEIGHT * score["event_score"], SENTIMENT_WEIGHT * score["sentiment_score"]],
            "Weight": ["60%", "40%"],
        })
        chart = px.bar(contribution, x="Weighted contribution", y="Component", orientation="h", text_auto=".2f", color="Component", color_discrete_sequence=["#2467a8", "#8c5bb3"])
        chart.update_layout(showlegend=False, xaxis_range=[0, 100], margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(chart, use_container_width=True)
        st.caption("Event risk = 60% Goldstein component + 40% full-range AvgTone component. Composite = 60% event risk + 40% VADER sentiment risk.")

    st.subheader("Event breakdown")
    event_summary = event_data.assign(
        GoldsteinScale=pd.to_numeric(event_data["GoldsteinScale"], errors="coerce"),
        AvgTone=pd.to_numeric(event_data["AvgTone"], errors="coerce"),
        NumMentions=pd.to_numeric(event_data["NumMentions"], errors="coerce"),
    )
    root_summary = (
        event_summary.groupby("EventRootCode", dropna=False)
        .agg(events=("EventCode", "size"), average_goldstein=("GoldsteinScale", "mean"), average_tone=("AvgTone", "mean"), mentions=("NumMentions", "sum"))
        .reset_index()
        .sort_values(["average_goldstein", "events"], ascending=[True, False])
    )
    first, second, third = st.columns(3)
    first.metric("Average Goldstein", f"{event_summary['GoldsteinScale'].mean():.2f}")
    second.metric("Average AvgTone", f"{event_summary['AvgTone'].mean():.2f}")
    third.metric("Total mentions", f"{event_summary['NumMentions'].sum():,.0f}")
    st.caption("EventRootCode is shown as reported by GDELT; the dashboard does not invent event-type labels.")
    st.dataframe(root_summary.head(10), use_container_width=True, hide_index=True)

    st.subheader("Source articles and VADER sentiment")
    articles["seendate"] = pd.to_datetime(articles["seendate"], errors="coerce")
    article_view = articles[["seendate", "title", "domain", "sentiment", "sentiment_score", "url"]].sort_values("seendate", ascending=False)
    st.dataframe(
        article_view,
        column_config={
            "seendate": st.column_config.DatetimeColumn("Seen date", format="YYYY-MM-DD"),
            "url": st.column_config.LinkColumn("Source link", display_text="Open article"),
            "sentiment_score": st.column_config.NumberColumn("VADER score", format="%.3f"),
        },
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Experimental ML result — not deployed"):
        st.write(
            "We tested whether the available historical patterns could predict next-day risk. "
            "They did not outperform simple baselines, so prediction is not used in this dashboard."
        )
        ml = pd.DataFrame({
            "Experiment": ["Risk-direction classification", "Next-day risk regression"],
            "Simple baseline": ["Majority baseline: 55.56% accuracy", "Naive persistence: 1.32 MAE"],
            "Tested model": ["Logistic Regression: 46.15% accuracy", "Linear Regression: 2.39 MAE"],
            "Live use": ["Not deployed", "Not deployed"],
        })
        st.dataframe(ml, use_container_width=True, hide_index=True)

    st.caption("Method correction: AvgTone is normalized across its full −100 to +100 range. Earlier ±10 clipping was removed because it understated tone variation.")


if __name__ == "__main__":
    main()
