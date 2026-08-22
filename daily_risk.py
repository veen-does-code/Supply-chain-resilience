import pandas as pd

# ==============================
# LOAD DATA
# ==============================

print("Loading sentiment data...")
sentiment = pd.read_csv("gdelt_sentiment.csv")

print("Loading event risk data...")
events = pd.read_csv("gdelt_event_risk.csv")


# ==============================
# SENTIMENT DAILY DATA
# ==============================

# Convert date
sentiment["seendate"] = pd.to_datetime(
    sentiment["seendate"],
    errors="coerce"
)

# Extract date
sentiment["date"] = sentiment["seendate"].dt.date

# Convert sentiment score to numeric
sentiment["sentiment_score"] = pd.to_numeric(
    sentiment["sentiment_score"],
    errors="coerce"
)

# Negative article ratio
sentiment["is_negative"] = (
    sentiment["sentiment"] == "Negative"
).astype(int)

daily_sentiment = sentiment.groupby("date").agg(
    article_count=("title", "count"),
    avg_sentiment=("sentiment_score", "mean"),
    negative_articles=("is_negative", "sum")
).reset_index()

daily_sentiment["negative_ratio"] = (
    daily_sentiment["negative_articles"]
    / daily_sentiment["article_count"]
)


# ==============================
# EVENT DAILY DATA
# ==============================

# SQLDATE is in YYYYMMDD format
events["date"] = pd.to_datetime(
    events["SQLDATE"].astype(str),
    format="%Y%m%d",
    errors="coerce"
).dt.date

# Convert numerical columns
events["GoldsteinScale"] = pd.to_numeric(
    events["GoldsteinScale"],
    errors="coerce"
)

events["AvgTone"] = pd.to_numeric(
    events["AvgTone"],
    errors="coerce"
)

events["NumMentions"] = pd.to_numeric(
    events["NumMentions"],
    errors="coerce"
)

daily_events = events.groupby("date").agg(
    event_count=("EventCode", "count"),
    avg_goldstein=("GoldsteinScale", "mean"),
    avg_tone=("AvgTone", "mean"),
    total_mentions=("NumMentions", "sum")
).reset_index()


# ==============================
# MERGE
# ==============================

daily = pd.merge(
    daily_sentiment,
    daily_events,
    on="date",
    how="outer"
)

daily = daily.sort_values("date")


# ==============================
# DISPLAY
# ==============================

print("\n==============================")
print("DAILY RISK DATA")
print("==============================")

print(daily.to_string(index=False))


# ==============================
# SAVE
# ==============================

daily.to_csv(
    "daily_risk.csv",
    index=False
)

print("\nSaved:")
print("daily_risk.csv")