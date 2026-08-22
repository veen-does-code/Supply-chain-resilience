import pandas as pd

# ==========================================
# LOAD DAILY DATA
# ==========================================

print("Loading daily risk data...")

df = pd.read_csv("daily_risk.csv")

print(f"Days available: {len(df)}")


# ==========================================
# NORMALIZE RISK COMPONENTS
# ==========================================

# Goldstein:
# -10 = highest risk
# +10 = lowest risk

df["goldstein_risk"] = (
    10 - df["avg_goldstein"]
) / 20


# AvgTone:
# We use -10 to +10 as the meaningful range.
# Values outside this range are clipped.

clipped_tone = df["avg_tone"].clip(-10, 10)

df["tone_risk"] = (
    10 - clipped_tone
) / 20


# VADER:
# VADER ranges from -1 to +1.
# Convert it to a risk score from 0 to 1.

df["sentiment_risk"] = (
    1 - df["avg_sentiment"]
) / 2


# ==========================================
# EVENT RISK
# ==========================================

df["event_risk"] = (
    0.60 * df["goldstein_risk"]
    + 0.40 * df["tone_risk"]
)


# ==========================================
# FINAL COMPOSITE RISK
# ==========================================

df["composite_risk"] = (
    0.60 * df["event_risk"]
    + 0.40 * df["sentiment_risk"]
)

df["risk_score"] = (
    df["composite_risk"] * 100
)


# ==========================================
# RISK CATEGORY
# ==========================================

def risk_category(score):

    if score < 25:
        return "Low"

    elif score < 50:
        return "Moderate"

    elif score < 75:
        return "High"

    else:
        return "Critical"


df["risk_category"] = df["risk_score"].apply(
    risk_category
)


# ==========================================
# DAILY CHANGE
# ==========================================

df["risk_change"] = df["risk_score"].diff()


# ==========================================
# TREND
# ==========================================

def determine_trend(change):

    if pd.isna(change):
        return "N/A"

    elif change > 2:
        return "Increasing"

    elif change < -2:
        return "Decreasing"

    else:
        return "Stable"


df["risk_trend"] = df["risk_change"].apply(
    determine_trend
)


# ==========================================
# DISPLAY
# ==========================================

print("\n==========================================")
print("       DAILY COMPOSITE RISK")
print("==========================================")

columns = [
    "date",
    "article_count",
    "event_count",
    "avg_sentiment",
    "avg_goldstein",
    "avg_tone",
    "risk_score",
    "risk_category",
    "risk_change",
    "risk_trend"
]

print(
    df[columns].to_string(index=False)
)


# ==========================================
# SAVE
# ==========================================

df.to_csv(
    "daily_composite_risk.csv",
    index=False
)

print("\n==========================================")
print("Saved:")
print("daily_composite_risk.csv")
print("==========================================")