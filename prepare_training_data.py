import pandas as pd

# ==========================================
# PREPARE TRAINING DATA
# ==========================================

print("Loading historical event data...")

df = pd.read_csv("historical_events.csv")

# Convert date column
df["date"] = pd.to_datetime(df["date"])

# ------------------------------------------------
# 1. Keep only the recent 2026 data
# ------------------------------------------------

df = df[
    (df["date"] >= "2026-07-02") &
    (df["date"] <= "2026-08-20")
].copy()

# Sort chronologically
df = df.sort_values("date").reset_index(drop=True)

print(f"Days available: {len(df)}")


# ------------------------------------------------
# 2. Calculate current GDELT risk score
# ------------------------------------------------
#
# Goldstein:
# -10 = highest risk
# +10 = lowest risk
#
# AvgTone:
# negative = more negative tone
#
# We normalize both to 0-1 risk.
# ------------------------------------------------

df["goldstein_risk"] = (10 - df["avg_goldstein"]) / 20

# Clip AvgTone because GDELT tone can go beyond +/-10
tone_clipped = df["avg_tone"].clip(-10, 10)

df["tone_risk"] = (10 - tone_clipped) / 20

# 60% Goldstein + 40% tone
df["risk_score"] = (
    0.6 * df["goldstein_risk"] +
    0.4 * df["tone_risk"]
) * 100


# ------------------------------------------------
# 3. Create trend features
# ------------------------------------------------

df["goldstein_change"] = df["avg_goldstein"].diff()

df["tone_change"] = df["avg_tone"].diff()

df["event_count_change"] = df["event_count"].diff()

df["risk_change"] = df["risk_score"].diff()


# ------------------------------------------------
# 4. Create prediction target
# ------------------------------------------------
#
# 1 = tomorrow's risk is higher
# 0 = tomorrow's risk is not higher
# ------------------------------------------------

df["risk_increase_tomorrow"] = (
    df["risk_score"].shift(-1) > df["risk_score"]
).astype(int)


# ------------------------------------------------
# 5. Remove rows where features are unavailable
# ------------------------------------------------

df = df.dropna().reset_index(drop=True)


# ------------------------------------------------
# 6. Remove final row
# ------------------------------------------------
#
# The final available day doesn't actually have
# tomorrow's data, so its target isn't meaningful.
# ------------------------------------------------

df = df.iloc[:-1].copy()


# ------------------------------------------------
# 7. Select useful columns
# ------------------------------------------------

training_columns = [
    "date",
    "event_count",
    "avg_goldstein",
    "avg_tone",
    "total_mentions",
    "risk_score",
    "goldstein_change",
    "tone_change",
    "event_count_change",
    "risk_change",
    "risk_increase_tomorrow"
]

training_df = df[training_columns]


# ------------------------------------------------
# 8. Display results
# ------------------------------------------------

print("\n==========================================")
print("       TRAINING DATA")
print("==========================================")

print(training_df.to_string(index=False))

print("\n------------------------------------------")
print("Target distribution:")
print("------------------------------------------")

print(
    training_df["risk_increase_tomorrow"]
    .value_counts()
    .sort_index()
)

print("\n------------------------------------------")
print("Target percentages:")
print("------------------------------------------")

print(
    training_df["risk_increase_tomorrow"]
    .value_counts(normalize=True)
    .sort_index() * 100
)

print("\n------------------------------------------")
print("Missing values:")
print("------------------------------------------")

print(training_df.isnull().sum())


# ------------------------------------------------
# 9. Save
# ------------------------------------------------

training_df.to_csv(
    "training_data.csv",
    index=False
)

print("\nSaved:")
print("training_data.csv")