import pandas as pd
import matplotlib.pyplot as plt


print("Loading historical risk data...")

# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv("historical_events.csv")

df["date"] = pd.to_datetime(df["date"])

df = df.sort_values("date").reset_index(drop=True)


# ============================================================
# GDELT RISK CALCULATION
# ============================================================

# Goldstein:
# -10 = highest conflict risk
# +10 = lowest conflict risk
#
# Convert to 0-1 risk scale

df["goldstein_risk"] = (
    (10 - df["avg_goldstein"]) / 20
)

df["goldstein_risk"] = df["goldstein_risk"].clip(0, 1)


# AvgTone:
# More negative tone = higher risk
#
# Same normalization used by the event-risk model

df["tone_risk"] = (
    (10 - df["avg_tone"]) / 20
)

df["tone_risk"] = df["tone_risk"].clip(0, 1)


# ============================================================
# GDELT EVENT RISK
# ============================================================

df["event_risk"] = (
    0.60 * df["goldstein_risk"]
    + 0.40 * df["tone_risk"]
) * 100


# ============================================================
# SENTIMENT RISK
# ============================================================

# For the historical trend we use the GDELT tone
# as the available daily sentiment signal.

df["sentiment_risk"] = (
    (10 - df["avg_tone"]) / 20
) * 100

df["sentiment_risk"] = df["sentiment_risk"].clip(0, 100)


# ============================================================
# COMPOSITE RISK
# ============================================================

df["risk_score"] = (
    0.60 * df["event_risk"]
    + 0.40 * df["sentiment_risk"]
)

df["risk_score"] = df["risk_score"].clip(0, 100)


# ============================================================
# ONLY USE RECENT DATA
# ============================================================

# Use the most recent 60 days available.

latest_date = df["date"].max()

start_date = latest_date - pd.Timedelta(days=60)

recent_df = df[
    df["date"] >= start_date
].copy()


# ============================================================
# DISPLAY
# ============================================================

print()
print("==========================================")
print("          RISK TREND ANALYSIS")
print("==========================================")

print(
    recent_df[
        [
            "date",
            "event_risk",
            "sentiment_risk",
            "risk_score"
        ]
    ].to_string(index=False)
)


# ============================================================
# CURRENT VALUE
# ============================================================

latest = recent_df.iloc[-1]

print()
print("------------------------------------------")
print("CURRENT RISK")
print("------------------------------------------")

print(
    f"Date          : {latest['date'].date()}"
)

print(
    f"Event Risk    : {latest['event_risk']:.2f}"
)

print(
    f"Sentiment Risk: {latest['sentiment_risk']:.2f}"
)

print(
    f"Risk Score    : {latest['risk_score']:.2f}"
)


# ============================================================
# PLOT
# ============================================================

plt.figure(figsize=(12, 6))

plt.plot(
    recent_df["date"],
    recent_df["risk_score"],
    marker="o",
    linewidth=2
)


# Medium threshold
plt.axhline(
    40,
    linestyle="--",
    linewidth=1,
    label="Medium Risk Threshold"
)


# High threshold
plt.axhline(
    70,
    linestyle="--",
    linewidth=1,
    label="High Risk Threshold"
)


# ============================================================
# LABELS
# ============================================================

plt.title(
    "Iran Composite Risk Trend"
)

plt.xlabel(
    "Date"
)

plt.ylabel(
    "Risk Score (0-100)"
)

plt.ylim(
    0,
    100
)

plt.grid(
    True,
    alpha=0.3
)

plt.legend()

plt.xticks(
    rotation=45
)

plt.tight_layout()


# ============================================================
# SAVE
# ============================================================

plt.savefig(
    "risk_trend.png",
    dpi=300,
    bbox_inches="tight"
)

print()
print("Saved:")
print("risk_trend.png")

plt.show()