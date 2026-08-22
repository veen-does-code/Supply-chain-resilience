import pandas as pd

INPUT_FILE = "gdelt_sentiment.csv"
OUTPUT_FILE = "gdelt_sentiment_risk.csv"

print("Loading sentiment data...")

df = pd.read_csv(INPUT_FILE)

print("Articles:", len(df))


# --------------------------------------------------
# 1. Convert VADER sentiment to risk
# --------------------------------------------------
#
# VADER sentiment_score ranges approximately:
#
# -1 = very negative
#  0 = neutral
# +1 = very positive
#
# For our risk model:
#
# negative sentiment -> higher risk
# positive sentiment -> lower risk
#
# Convert [-1, +1] to [0, 1]
#
# -1 -> 1.0 risk
#  0 -> 0.5 risk
# +1 -> 0.0 risk

df["sentiment_risk"] = (
    1 - df["sentiment_score"]
) / 2


# --------------------------------------------------
# 2. Convert to 0-100
# --------------------------------------------------

df["sentiment_risk_score"] = (
    df["sentiment_risk"] * 100
)


# --------------------------------------------------
# 3. Display article-level results
# --------------------------------------------------

print("\nArticle sentiment risk:")

print(
    df[
        [
            "title",
            "sentiment",
            "sentiment_score",
            "sentiment_risk",
            "sentiment_risk_score"
        ]
    ].to_string(index=False)
)


# --------------------------------------------------
# 4. Calculate average sentiment risk
# --------------------------------------------------

average_sentiment_risk = df["sentiment_risk"].mean()

average_sentiment_score = (
    average_sentiment_risk * 100
)


print("\n==============================")
print("ARTICLE SENTIMENT RISK")
print("==============================")

print(
    f"Average VADER sentiment: "
    f"{df['sentiment_score'].mean():.4f}"
)

print(
    f"Average sentiment risk: "
    f"{average_sentiment_score:.2f} / 100"
)


# --------------------------------------------------
# 5. Risk category
# --------------------------------------------------

if average_sentiment_score < 25:
    category = "Low"

elif average_sentiment_score < 50:
    category = "Moderate"

elif average_sentiment_score < 75:
    category = "High"

else:
    category = "Critical"


print(f"Risk Category: {category}")


# --------------------------------------------------
# 6. Save
# --------------------------------------------------

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print(
    f"\nSaved sentiment risk data to: "
    f"{OUTPUT_FILE}"
)