import pandas as pd

filename = "20260820.export.CSV.zip"

# Columns we want from the GDELT Event dataset
columns = [
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

# GDELT columns are numbered from 0
usecols = [
    0,   # GLOBALEVENTID
    1,   # SQLDATE
    26,  # EventCode
    27,  # EventBaseCode
    28,  # EventRootCode
    29,  # QuadClass
    30,  # GoldsteinScale
    31,  # NumMentions
    32,  # NumSources
    33,  # NumArticles
    34,  # AvgTone
    57   # SOURCEURL
]

print("Reading GDELT event data...")

df = pd.read_csv(
    filename,
    sep="\t",
    header=None,
    names=columns,
    usecols=usecols,
    compression="zip",
    low_memory=False
)

print("\nNumber of events:", len(df))

print("\nColumns:")
print(df.columns.tolist())

print("\nFirst 5 events:")
print(df.head().to_string())

print("\n\nGoldstein statistics:")
print(df["GoldsteinScale"].describe())

print("\n\nGoldstein examples:")
print(
    df[
        [
            "EventCode",
            "GoldsteinScale",
            "NumMentions",
            "NumSources",
            "SOURCEURL"
        ]
    ].head(20).to_string(index=False)
)

print("\n\nMissing values:")
print(df.isnull().sum())