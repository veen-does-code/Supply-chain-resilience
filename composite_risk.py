import pandas as pd

EVENT_FILE = "gdelt_event_risk.csv"
SENTIMENT_FILE = "gdelt_sentiment_risk.csv"

print("Loading risk data...")

# --------------------------------------------------
# 1. Load GDELT event risk
# --------------------------------------------------

events = pd.read_csv(EVENT_FILE)

event_risk = (
    events["event_risk"] * events["NumMentions"]
).sum() / events["NumMentions"].sum()

event_risk_score = event_risk * 100


# --------------------------------------------------
# 2. Load VADER sentiment risk
# --------------------------------------------------

sentiment = pd.read_csv(SENTIMENT_FILE)

sentiment_risk = sentiment["sentiment_risk"].mean()

sentiment_risk_score = sentiment_risk * 100


# --------------------------------------------------
# 3. Combine the two signals
# --------------------------------------------------

EVENT_WEIGHT = 0.60
SENTIMENT_WEIGHT = 0.40

final_risk = (
    EVENT_WEIGHT * event_risk_score
    +
    SENTIMENT_WEIGHT * sentiment_risk_score
)


# --------------------------------------------------
# 4. Risk category
# --------------------------------------------------

if final_risk < 25:
    category = "Low"

elif final_risk < 50:
    category = "Moderate"

elif final_risk < 75:
    category = "High"

else:
    category = "Critical"


# --------------------------------------------------
# 5. Display
# --------------------------------------------------

print("\n================================")
print("      COMPOSITE RISK MODEL")
print("================================")

print(f"\nGDELT Event Risk      : {event_risk_score:.2f} / 100")
print(f"VADER Sentiment Risk  : {sentiment_risk_score:.2f} / 100")

print("\nWeights:")
print(f"Event Risk            : {EVENT_WEIGHT * 100:.0f}%")
print(f"Sentiment Risk        : {SENTIMENT_WEIGHT * 100:.0f}%")

print("\n--------------------------------")

print(f"FINAL RISK SCORE      : {final_risk:.2f} / 100")
print(f"RISK CATEGORY         : {category}")

print("================================")