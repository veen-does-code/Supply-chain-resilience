import pandas as pd
from sklearn.metrics import accuracy_score

print("Loading training data...")

df = pd.read_csv("training_data.csv")

target = "risk_increase_tomorrow"

# -----------------------------------------
# BASELINE MODELS
# -----------------------------------------

y = df[target]

always_1 = [1] * len(y)
always_0 = [0] * len(y)

print()
print("==============================")
print("        BASELINE MODELS")
print("==============================")

print(
    f"Always predict 1: "
    f"{accuracy_score(y, always_1) * 100:.2f}%"
)

print(
    f"Always predict 0: "
    f"{accuracy_score(y, always_0) * 100:.2f}%"
)


# -----------------------------------------
# CORRELATIONS
# -----------------------------------------

features = [
    "event_count",
    "avg_goldstein",
    "avg_tone",
    "total_mentions",
    "goldstein_change",
    "tone_change",
    "event_count_change",
    "risk_change"
]

print()
print("==============================")
print(" FEATURE CORRELATIONS")
print("==============================")

correlations = (
    df[features + [target]]
    .corr()[target]
    .drop(target)
    .sort_values(key=abs, ascending=False)
)

print(correlations)


# -----------------------------------------
# TARGET DISTRIBUTION
# -----------------------------------------

print()
print("==============================")
print(" TARGET DISTRIBUTION")
print("==============================")

print(df[target].value_counts())

print()
print(
    df[target]
    .value_counts(normalize=True)
    .mul(100)
)


# -----------------------------------------
# DATA RANGE
# -----------------------------------------

print()
print("==============================")
print(" DATA RANGE")
print("==============================")

print("First date:", df["date"].iloc[0])
print("Last date :", df["date"].iloc[-1])
print("Rows      :", len(df))