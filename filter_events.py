import pandas as pd

filename = "20260820.export.CSV.zip"

columns = [
    "GLOBALEVENTID",
    "SQLDATE",
    "Actor1Name",
    "Actor1CountryCode",
    "Actor2Name",
    "Actor2CountryCode",
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
    0,      # GLOBALEVENTID
    1,      # SQLDATE
    5,      # Actor1Name
    7,      # Actor1CountryCode
    15,     # Actor2Name
    17,     # Actor2CountryCode
    26,     # EventCode
    27,     # EventBaseCode
    28,     # EventRootCode
    29,     # QuadClass
    30,     # GoldsteinScale
    31,     # NumMentions
    32,     # NumSources
    33,     # NumArticles
    34,     # AvgTone
    57      # SOURCEURL
]

print("Reading GDELT events...")

df = pd.read_csv(
    filename,
    sep="\t",
    header=None,
    names=columns,
    usecols=usecols,
    compression="zip",
    low_memory=False
)

print("Total events:", len(df))


# --------------------------------------------------
# Keep only August 20, 2026
# --------------------------------------------------

df = df[df["SQLDATE"] == 20260820].copy()

print("Events on 2026-08-20:", len(df))


# --------------------------------------------------
# Filter for Iran-related events
# --------------------------------------------------

iran_events = df[
    (df["Actor1CountryCode"] == "IRN") |
    (df["Actor2CountryCode"] == "IRN") |
    (df["Actor1Name"].fillna("").str.contains(
        "IRAN", case=False, na=False
    )) |
    (df["Actor2Name"].fillna("").str.contains(
        "IRAN", case=False, na=False
    ))
].copy()


print("\nIran-related events:", len(iran_events))


# --------------------------------------------------
# Display sample
# --------------------------------------------------

print("\nSample Iran-related events:")

print(
    iran_events[
        [
            "Actor1Name",
            "Actor1CountryCode",
            "Actor2Name",
            "Actor2CountryCode",
            "EventCode",
            "GoldsteinScale",
            "NumMentions",
            "NumSources",
            "AvgTone",
            "SOURCEURL"
        ]
    ]
    .head(30)
    .to_string(index=False)
)


# --------------------------------------------------
# Goldstein statistics
# --------------------------------------------------

print("\nGoldstein statistics:")

print(
    iran_events["GoldsteinScale"].describe()
)


# --------------------------------------------------
# AvgTone statistics
# --------------------------------------------------

print("\nAvgTone statistics:")

print(
    iran_events["AvgTone"].describe()
)

iran_events.to_csv(
    "iran_events.csv",
    index=False
)

print("\nSaved as: iran_events.csv")