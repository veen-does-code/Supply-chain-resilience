import pandas as pd

print("Loading historical event data...")

# -----------------------------------------
# LOAD HISTORICAL DATA
# -----------------------------------------

df = pd.read_csv("historical_events.csv")

# Convert date to datetime
df["date"] = pd.to_datetime(df["date"])

# Sort chronologically
df = df.sort_values("date").reset_index(drop=True)

print(f"Days available: {len(df)}")


# -----------------------------------------
# CALCULATE RISK SCORE
# -----------------------------------------

# Goldstein:
# -10 = highest risk
# +10 = lowest risk
goldstein_risk = (10 - df["avg_goldstein"]) / 20

# AvgTone:
# Clip to -10 to +10
# -10 = highest risk
# +10 = lowest risk
tone_clipped = df["avg_tone"].clip(-10, 10)

tone_risk = (10 - tone_clipped) / 20

# Combine the two signals
df["risk_score"] = (
    0.6 * goldstein_risk +
    0.4 * tone_risk
) * 100


# -----------------------------------------
# CALCULATE CHANGES FROM PREVIOUS DAY
# -----------------------------------------

df["goldstein_change"] = (
    df["avg_goldstein"].diff()
)

df["tone_change"] = (
    df["avg_tone"].diff()
)

df["event_count_change"] = (
    df["event_count"].diff()
)

df["risk_change"] = (
    df["risk_score"].diff()
)


# -----------------------------------------
# CREATE TOMORROW'S RISK TARGET
# -----------------------------------------

# The target for today's row is tomorrow's risk score.
#
# Example:
#
# Aug 17 → today's risk = 55.75
#          tomorrow_risk = Aug 18 risk = 57.01
#
# Aug 18 → today's risk = 57.01
#          tomorrow_risk = Aug 19 risk = 58.12

df["tomorrow_risk"] = (
    df["risk_score"].shift(-1)
)


# -----------------------------------------
# KEEP THE OLD CLASSIFICATION TARGET
# -----------------------------------------

# This is still useful later if we want to compare
# regression against classification.

df["risk_increase_tomorrow"] = (
    df["tomorrow_risk"] > df["risk_score"]
).astype(int)


# -----------------------------------------
# REMOVE ROWS THAT CANNOT BE USED
# -----------------------------------------

# The final day has no "tomorrow" data,
# so it cannot be used for training.

df = df.dropna(
    subset=[
        "tomorrow_risk",
        "goldstein_change",
        "tone_change",
        "event_count_change",
        "risk_change"
    ]
).reset_index(drop=True)


# -----------------------------------------
# SELECT TRAINING DATA COLUMNS
# -----------------------------------------

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
    "tomorrow_risk",
    "risk_increase_tomorrow"
]

training_data = df[training_columns]


# -----------------------------------------
# DISPLAY RESULTS
# -----------------------------------------

print()
print("==========================================")
print("       TRAINING DATA")
print("==========================================")

print(
    training_data.to_string(index=False)
)


# -----------------------------------------
# TARGET DISTRIBUTION
# -----------------------------------------

print()
print("------------------------------------------")
print("Risk increase target distribution:")
print("------------------------------------------")

print(
    training_data["risk_increase_tomorrow"]
    .value_counts()
)


print()
print("------------------------------------------")
print("Risk increase percentages:")
print("------------------------------------------")

print(
    training_data["risk_increase_tomorrow"]
    .value_counts(normalize=True)
    .mul(100)
)


# -----------------------------------------
# TOMORROW RISK STATISTICS
# -----------------------------------------

print()
print("------------------------------------------")
print("Tomorrow risk statistics:")
print("------------------------------------------")

print(
    training_data["tomorrow_risk"].describe()
)


# -----------------------------------------
# MISSING VALUES
# -----------------------------------------

print()
print("------------------------------------------")
print("Missing values:")
print("------------------------------------------")

print(
    training_data.isnull().sum()
)


# -----------------------------------------
# SAVE TRAINING DATA
# -----------------------------------------

training_data.to_csv(
    "training_data.csv",
    index=False
)

print()
print("Saved:")
print("training_data.csv")