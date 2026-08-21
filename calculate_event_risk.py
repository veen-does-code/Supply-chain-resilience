import pandas as pd

INPUT_FILE = "iran_events.csv"
OUTPUT_FILE = "gdelt_event_risk.csv"

print("Loading Iran-related events...")

df = pd.read_csv(INPUT_FILE)

print("Events:", len(df))


# --------------------------------------------------
# 1. Normalize Goldstein
# --------------------------------------------------
# Goldstein:
# -10 = highest potential instability
# +10 = lowest potential instability
#
# Convert to:
# 0 = low risk
# 1 = high risk

df["goldstein_risk"] = (10 - df["GoldsteinScale"]) / 20


# --------------------------------------------------
# 2. Normalize AvgTone
# --------------------------------------------------
# AvgTone is approximately centered around 0.
#
# We clip it to [-10, +10] so extreme values
# don't dominate the calculation.
#
# -10 = high risk
# +10 = low risk

tone_clipped = df["AvgTone"].clip(-10, 10)

df["tone_risk"] = (10 - tone_clipped) / 20


# --------------------------------------------------
# 3. Combine Goldstein + AvgTone
# --------------------------------------------------

df["event_risk"] = (
    0.60 * df["goldstein_risk"]
    +
    0.40 * df["tone_risk"]
)


# --------------------------------------------------
# 4. Weight by number of mentions
# --------------------------------------------------

df["weighted_risk"] = (
    df["event_risk"] * df["NumMentions"]
)


# --------------------------------------------------
# 5. Calculate overall weighted risk
# --------------------------------------------------

total_mentions = df["NumMentions"].sum()

overall_risk = (
    df["weighted_risk"].sum()
    /
    total_mentions
)


risk_score = overall_risk * 100


# --------------------------------------------------
# 6. Display results
# --------------------------------------------------

print("\n==============================")
print("GDELT EVENT RISK")
print("==============================")

print(f"Goldstein weight : 60%")
print(f"AvgTone weight   : 40%")

print(f"\nTotal mentions: {total_mentions:,}")

print(f"\nGDELT Event Risk: {overall_risk:.4f}")

print(f"GDELT Risk Score: {risk_score:.2f} / 100")


# --------------------------------------------------
# 7. Risk category
# --------------------------------------------------

if risk_score < 25:
    category = "Low"
elif risk_score < 50:
    category = "Moderate"
elif risk_score < 75:
    category = "High"
else:
    category = "Critical"


print(f"Risk Category: {category}")


# --------------------------------------------------
# 8. Show highest-risk events
# --------------------------------------------------

print("\nHighest-risk events:")

highest = df.sort_values(
    "event_risk",
    ascending=False
)

print(
    highest[
        [
            "EventCode",
            "GoldsteinScale",
            "AvgTone",
            "NumMentions",
            "goldstein_risk",
            "tone_risk",
            "event_risk",
            "SOURCEURL"
        ]
    ]
    .head(10)
    .to_string(index=False)
)


# --------------------------------------------------
# 9. Save
# --------------------------------------------------

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print(f"\nSaved event risk data to: {OUTPUT_FILE}")