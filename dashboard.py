"""Iran Risk Monitor dashboard.

Run from the project folder with:
    python dashboard.py

The dashboard intentionally uses the same historical 60/40 composite
calculation as risk_trend.py and risk_explanation.py.  It does not load or
display any predictive ML model.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import pandas as pd


# These values match the existing risk_trend.py / risk_explanation.py logic.
GDELT_WEIGHT = 0.60
SENTIMENT_WEIGHT = 0.40
MEDIUM_THRESHOLD = 40
HIGH_THRESHOLD = 70
DATA_FILE = Path(__file__).with_name("historical_events.csv")
OUTPUT_FILE = Path(__file__).with_name("iran_risk_dashboard.png")

REQUIRED_COLUMNS = {
    "date",
    "event_count",
    "avg_goldstein",
    "avg_tone",
    "total_mentions",
    "total_sources",
    "total_articles",
}


def load_risk_data() -> pd.DataFrame:
    """Load the existing history and apply the established daily scoring logic."""
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Could not find {DATA_FILE.name}. Put dashboard.py beside the CSV."
        )

    df = pd.read_csv(DATA_FILE)
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError(
            f"{DATA_FILE.name} is missing required column(s): {', '.join(sorted(missing))}"
        )
    if len(df) < 2:
        raise ValueError("At least two historical observations are required for day-over-day changes.")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Goldstein: -10 indicates highest conflict risk, +10 lowest.
    df["goldstein_risk"] = ((10 - df["avg_goldstein"]) / 20).clip(0, 1)

    # More negative AvgTone means higher risk.
    df["tone_risk"] = ((10 - df["avg_tone"]) / 20).clip(0, 1)

    # Exact component and composite weighting already used in the project.
    df["event_risk"] = (
        0.60 * df["goldstein_risk"] + 0.40 * df["tone_risk"]
    ) * 100
    df["sentiment_risk"] = (df["tone_risk"] * 100).clip(0, 100)
    df["risk_score"] = (
        GDELT_WEIGHT * df["event_risk"]
        + SENTIMENT_WEIGHT * df["sentiment_risk"]
    ).clip(0, 100)
    return df


def risk_category(score: float) -> str:
    if score < MEDIUM_THRESHOLD:
        return "LOW"
    if score < HIGH_THRESHOLD:
        return "MEDIUM"
    return "HIGH"


def category_color(category: str) -> str:
    return {"LOW": "#2e8b57", "MEDIUM": "#e69f00", "HIGH": "#c0392b"}[category]


def change_text(value: float, decimals: int = 0) -> str:
    return f"{value:+,.{decimals}f}"


def interpretation(latest: pd.Series, previous: pd.Series) -> list[str]:
    event_change = latest["event_count"] - previous["event_count"]
    mention_change = latest["total_mentions"] - previous["total_mentions"]
    goldstein_message = (
        "Negative Goldstein score: events are skewed toward conflict-oriented activity."
        if latest["avg_goldstein"] < 0
        else "Positive Goldstein score: events are less conflict-oriented."
    )
    tone_message = (
        "Media tone is negative."
        if latest["avg_tone"] < 0
        else "Media tone is positive."
    )
    event_message = (
        f"Event activity increased by {event_change:,.0f} versus the previous available day."
        if event_change > 0
        else f"Event activity decreased by {abs(event_change):,.0f} versus the previous available day."
        if event_change < 0
        else "Event activity was unchanged versus the previous available day."
    )
    mention_message = (
        f"Media mentions increased by {mention_change:,.0f}."
        if mention_change > 0
        else f"Media mentions decreased by {abs(mention_change):,.0f}."
        if mention_change < 0
        else "Media mentions were unchanged."
    )
    return [goldstein_message, tone_message, event_message, mention_message]


def build_dashboard(df: pd.DataFrame) -> None:
    latest = df.iloc[-1]
    previous = df.iloc[-2]
    score = float(latest["risk_score"])
    category = risk_category(score)
    color = category_color(category)

    latest_date = df["date"].max()
    recent = df[df["date"] >= latest_date - pd.Timedelta(days=60)].copy()

    plt.style.use("seaborn-v0_8-whitegrid")
    fig = plt.figure(figsize=(16, 10), facecolor="#f7f9fc")
    grid = GridSpec(2, 3, figure=fig, height_ratios=[1, 1.35], wspace=0.32, hspace=0.42)
    fig.suptitle("IRAN RISK MONITOR", fontsize=23, fontweight="bold", color="#172b4d", y=0.97)
    fig.text(
        0.5, 0.935,
        f"Latest available observation: {latest['date'].date()}  |  Interpretable 60/40 GDELT composite",
        ha="center", fontsize=10.5, color="#52616b",
    )

    # Current score card.
    ax_score = fig.add_subplot(grid[0, 0])
    ax_score.set_axis_off()
    ax_score.text(0.5, 0.82, "CURRENT RISK", ha="center", fontsize=13, fontweight="bold", color="#34495e")
    ax_score.text(0.5, 0.48, f"{score:.2f}", ha="center", fontsize=46, fontweight="bold", color=color)
    ax_score.text(0.5, 0.28, "/ 100", ha="center", fontsize=14, color="#52616b")
    ax_score.text(
        0.5, 0.08, f"{category} RISK", ha="center", va="center", fontsize=15,
        fontweight="bold", color="white",
        bbox={"boxstyle": "round,pad=0.45", "facecolor": color, "edgecolor": "none"},
    )

    # Weighted components.
    ax_components = fig.add_subplot(grid[0, 1])
    component_names = ["GDELT Event\nRisk (60%)", "Sentiment\nRisk (40%)"]
    component_values = [latest["event_risk"], latest["sentiment_risk"]]
    bars = ax_components.bar(component_names, component_values, color=["#2c7fb8", "#8c6bb1"], width=0.58)
    ax_components.set_title("RISK COMPONENTS", fontweight="bold", color="#34495e", pad=12)
    ax_components.set_ylabel("Score (0–100)")
    ax_components.set_ylim(0, 100)
    ax_components.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, component_values):
        ax_components.text(bar.get_x() + bar.get_width() / 2, value + 3, f"{value:.2f}", ha="center", fontweight="bold")

    # Current conditions.
    ax_conditions = fig.add_subplot(grid[0, 2])
    ax_conditions.set_axis_off()
    ax_conditions.set_title("CURRENT CONDITIONS", fontweight="bold", color="#34495e", pad=12)
    conditions = [
        ("Event count", f"{latest['event_count']:,.0f}"),
        ("Total mentions", f"{latest['total_mentions']:,.0f}"),
        ("Total sources", f"{latest['total_sources']:,.0f}"),
        ("Total articles", f"{latest['total_articles']:,.0f}"),
        ("Average Goldstein", f"{latest['avg_goldstein']:.2f}"),
        ("Average tone", f"{latest['avg_tone']:.2f}"),
    ]
    for index, (label, value) in enumerate(conditions):
        y = 0.89 - index * 0.145
        ax_conditions.text(0.03, y, label, fontsize=11, color="#52616b", transform=ax_conditions.transAxes)
        ax_conditions.text(0.97, y, value, fontsize=11, fontweight="bold", ha="right", color="#172b4d", transform=ax_conditions.transAxes)
        ax_conditions.plot([0.03, 0.97], [y - 0.055, y - 0.055], color="#dfe6ed", lw=0.8, transform=ax_conditions.transAxes)

    # Historical trend.
    ax_trend = fig.add_subplot(grid[1, :2])
    ax_trend.plot(recent["date"], recent["risk_score"], color="#2c7fb8", marker="o", markersize=4, linewidth=2.4, label="Composite risk")
    ax_trend.axhspan(0, MEDIUM_THRESHOLD, color="#2e8b57", alpha=0.06)
    ax_trend.axhspan(MEDIUM_THRESHOLD, HIGH_THRESHOLD, color="#e69f00", alpha=0.06)
    ax_trend.axhspan(HIGH_THRESHOLD, 100, color="#c0392b", alpha=0.06)
    ax_trend.axhline(MEDIUM_THRESHOLD, color="#e69f00", linestyle="--", linewidth=1, label="Medium threshold (40)")
    ax_trend.axhline(HIGH_THRESHOLD, color="#c0392b", linestyle="--", linewidth=1, label="High threshold (70)")
    ax_trend.scatter([latest["date"]], [score], s=95, color=color, edgecolor="white", linewidth=1.5, zorder=3)
    ax_trend.annotate(f"{score:.2f}", (latest["date"], score), xytext=(8, 10), textcoords="offset points", fontweight="bold", color=color)
    ax_trend.set_title("HISTORICAL COMPOSITE RISK TREND (LATEST 60 DAYS)", fontweight="bold", color="#34495e", pad=10)
    ax_trend.set_xlabel("Date")
    ax_trend.set_ylabel("Risk score (0–100)")
    ax_trend.set_ylim(0, 100)
    ax_trend.legend(loc="upper left", ncols=3, fontsize=9)
    ax_trend.grid(alpha=0.25)
    fig.autofmt_xdate(rotation=30)

    # Explainability and changes.
    ax_why = fig.add_subplot(grid[1, 2])
    ax_why.set_axis_off()
    ax_why.set_title("WHY THIS SCORE?", fontweight="bold", color="#34495e", pad=10)
    changes = [
        ("Events", change_text(latest["event_count"] - previous["event_count"])),
        ("Mentions", change_text(latest["total_mentions"] - previous["total_mentions"])),
        ("Goldstein", change_text(latest["avg_goldstein"] - previous["avg_goldstein"], 2)),
        ("Tone", change_text(latest["avg_tone"] - previous["avg_tone"], 2)),
    ]
    ax_why.text(0.03, 0.93, "Changes from previous available day", transform=ax_why.transAxes, fontsize=9.5, color="#52616b")
    for index, (label, value) in enumerate(changes):
        y = 0.84 - index * 0.07
        ax_why.text(0.04, y, label, transform=ax_why.transAxes, fontsize=10, color="#52616b")
        ax_why.text(0.62, y, value, transform=ax_why.transAxes, fontsize=10, fontweight="bold", color="#172b4d")
    ax_why.plot([0.03, 0.97], [0.53, 0.53], color="#dfe6ed", lw=1, transform=ax_why.transAxes)
    for index, message in enumerate(interpretation(latest, previous)):
        ax_why.text(0.04, 0.46 - index * 0.11, f"• {message}", transform=ax_why.transAxes, fontsize=9.8, va="top", wrap=True, color="#263238")

    fig.text(0.5, 0.012, "Scoring: 60% GDELT event risk + 40% tone-based sentiment risk. No predictive ML is deployed.", ha="center", fontsize=9.5, color="#52616b")
    fig.savefig(OUTPUT_FILE, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"Saved dashboard image: {OUTPUT_FILE.name}")
    plt.show()


def main() -> None:
    print("Loading historical risk data...")
    data = load_risk_data()
    latest = data.iloc[-1]
    print(f"Current risk: {latest['risk_score']:.2f} / 100 ({risk_category(latest['risk_score'])})")
    print(f"Components: event {latest['event_risk']:.2f}, sentiment {latest['sentiment_risk']:.2f}")
    build_dashboard(data)


if __name__ == "__main__":
    main()
