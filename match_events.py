import pandas as pd

# --------------------------------------------------
# 1. Load our sentiment dataset
# --------------------------------------------------

articles = pd.read_csv("gdelt_sentiment.csv")

print("Articles:", len(articles))


# --------------------------------------------------
# 2. Load GDELT Event data
# --------------------------------------------------

event_columns = [
    "GLOBALEVENTID",
    "SQLDATE",
    "EventCode",
    "EventBaseCode",
    "EventRootCode",
    "QuadClass",
    "GoldsteinScale",
    "NumMentions",
    "NumSources",
    "NumArticles",
    "AvgTone",
    "SOURCEURL"
]

usecols = [
    0,
    1,
    26,
    27,
    28,
    29,
    30,
    31,
    32,
    33,
    34,
    57
]

print("Reading event data...")

events = pd.read_csv(
    "20260820.export.CSV.zip",
    sep="\t",
    header=None,
    names=event_columns,
    usecols=usecols,
    compression="zip",
    low_memory=False
)

print("Events:", len(events))


# --------------------------------------------------
# 3. Clean URLs
# --------------------------------------------------

articles["url_clean"] = (
    articles["url"]
    .str.lower()
    .str.rstrip("/")
)

events["url_clean"] = (
    events["SOURCEURL"]
    .str.lower()
    .str.rstrip("/")
)


# --------------------------------------------------
# 4. Match article URLs to event URLs
# --------------------------------------------------

matched = articles.merge(
    events,
    on="url_clean",
    how="left",
    suffixes=("_article", "_event")
)


# --------------------------------------------------
# 5. Check matching
# --------------------------------------------------

matched_articles = matched["GLOBALEVENTID"].notna().sum()

print("\nMatched event records:", matched_articles)

print(
    "Articles with at least one event:",
    matched.groupby("url_clean")["GLOBALEVENTID"]
    .count()
    .gt(0)
    .sum()
)

print(
    "Articles with no event:",
    matched.groupby("url_clean")["GLOBALEVENTID"]
    .count()
    .eq(0)
    .sum()
)


# --------------------------------------------------
# 6. Show matches
# --------------------------------------------------

print("\nSample matches:")

print(
    matched[
        [
            "title",
            "sentiment_score",
            "GoldsteinScale",
            "NumMentions",
            "NumSources",
            "SOURCEURL"
        ]
    ]
    .dropna(subset=["GoldsteinScale"])
    .head(20)
    .to_string(index=False)
)