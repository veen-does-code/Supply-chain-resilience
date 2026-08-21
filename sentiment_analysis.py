import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ----------------------------------------
# 1. Load our cleaned GDELT dataset
# ----------------------------------------

df = pd.read_csv("gdelt_energy_clean.csv")

print("Number of articles:", len(df))


# ----------------------------------------
# 2. Create VADER sentiment analyzer
# ----------------------------------------

analyzer = SentimentIntensityAnalyzer()


# ----------------------------------------
# 3. Function to calculate sentiment
# ----------------------------------------

def get_sentiment(text):

    scores = analyzer.polarity_scores(text)

    compound = scores["compound"]

    if compound >= 0.05:
        sentiment = "Positive"

    elif compound <= -0.05:
        sentiment = "Negative"

    else:
        sentiment = "Neutral"

    return sentiment, compound


# ----------------------------------------
# 4. Apply sentiment analysis
# ----------------------------------------

results = df["title"].apply(get_sentiment)


# ----------------------------------------
# 5. Add results to dataframe
# ----------------------------------------

df["sentiment"] = results.apply(lambda x: x[0])

df["sentiment_score"] = results.apply(lambda x: x[1])


# ----------------------------------------
# 6. Display results
# ----------------------------------------

print("\nSentiment results:\n")

print(
    df[
        [
            "title",
            "sentiment",
            "sentiment_score"
        ]
    ].to_string(index=False)
)


# ----------------------------------------
# 7. Count sentiments
# ----------------------------------------

print("\n\nSentiment distribution:")

print(df["sentiment"].value_counts())


# ----------------------------------------
# 8. Save the new dataset
# ----------------------------------------

df.to_csv("gdelt_sentiment.csv", index=False)

print("\nSentiment dataset saved!")

print("File: gdelt_sentiment.csv")