import pandas as pd
import os
import zipfile


# ==========================================
# SETTINGS
# ==========================================

# Change these if you have more ZIP files
files = [
    "20260801.export.CSV.zip",
    "20260802.export.CSV.zip",
    "20260803.export.CSV.zip",
    "20260804.export.CSV.zip",
    "20260805.export.CSV.zip",
    "20260806.export.CSV.zip",
    "20260807.export.CSV.zip",
    "20260808.export.CSV.zip",
    "20260809.export.CSV.zip",
    "20260810.export.CSV.zip",
    "20260811.export.CSV.zip",
    "20260812.export.CSV.zip",
    "20260813.export.CSV.zip",
    "20260814.export.CSV.zip",
    "20260815.export.CSV.zip",
    "20260816.export.CSV.zip",
    "20260817.export.CSV.zip",
    "20260818.export.CSV.zip",
    "20260819.export.CSV.zip",
    "20260820.export.CSV.zip"
]


# ==========================================
# GDELT COLUMN NAMES
# ==========================================

columns = [
    "GLOBALEVENTID",
    "SQLDATE",
    "MonthYear",
    "Year",
    "FractionDate",
    "Actor1Code",
    "Actor1Name",
    "Actor1CountryCode",
    "Actor1KnownGroupCode",
    "Actor1EthnicCode",
    "Actor1Religion1Code",
    "Actor1Religion2Code",
    "Actor1Type1Code",
    "Actor1Type2Code",
    "Actor1Type3Code",
    "Actor2Code",
    "Actor2Name",
    "Actor2CountryCode",
    "Actor2KnownGroupCode",
    "Actor2EthnicCode",
    "Actor2Religion1Code",
    "Actor2Religion2Code",
    "Actor2Type1Code",
    "Actor2Type2Code",
    "Actor2Type3Code",
    "IsRootEvent",
    "EventCode",
    "EventBaseCode",
    "EventRootCode",
    "QuadClass",
    "GoldsteinScale",
    "NumMentions",
    "NumSources",
    "NumArticles",
    "AvgTone",
    "Actor1Geo_Type",
    "Actor1Geo_FullName",
    "Actor1Geo_CountryCode",
    "Actor1Geo_ADM1Code",
    "Actor1Geo_Lat",
    "Actor1Geo_Long",
    "Actor1Geo_FeatureID",
    "Actor2Geo_Type",
    "Actor2Geo_FullName",
    "Actor2Geo_CountryCode",
    "Actor2Geo_ADM1Code",
    "Actor2Geo_Lat",
    "Actor2Geo_Long",
    "Actor2Geo_FeatureID",
    "ActionGeo_Type",
    "ActionGeo_FullName",
    "ActionGeo_CountryCode",
    "ActionGeo_ADM1Code",
    "ActionGeo_Lat",
    "ActionGeo_Long",
    "ActionGeo_FeatureID",
    "DATEADDED",
    "SOURCEURL"
]


all_events = []


# ==========================================
# READ FILES
# ==========================================

for filename in files:

    print(f"\nReading {filename}...")

    if not os.path.exists(filename):
        print("File not found!")
        continue

    with zipfile.ZipFile(filename) as z:

        csv_name = z.namelist()[0]

        with z.open(csv_name) as f:

            df = pd.read_csv(
                f,
                sep="\t",
                header=None,
                names=columns,
                encoding="utf-8",
                low_memory=False
            )

    print(f"Events loaded: {len(df)}")

    all_events.append(df)


# ==========================================
# COMBINE
# ==========================================

events = pd.concat(
    all_events,
    ignore_index=True
)

print("\nTotal events:", len(events))


# ==========================================
# CONVERT DATE
# ==========================================

events["date"] = pd.to_datetime(
    events["SQLDATE"].astype(str),
    format="%Y%m%d",
    errors="coerce"
).dt.date


# ==========================================
# IRAN FILTER
# ==========================================

iran_events = events[
    (events["Actor1CountryCode"] == "IRN") |
    (events["Actor2CountryCode"] == "IRN") |
    (events["Actor1Name"].astype(str).str.contains(
        "Iran",
        case=False,
        na=False
    )) |
    (events["Actor2Name"].astype(str).str.contains(
        "Iran",
        case=False,
        na=False
    ))
].copy()


print("\nIran-related events:", len(iran_events))


# ==========================================
# NUMERIC COLUMNS
# ==========================================

numeric_columns = [
    "GoldsteinScale",
    "AvgTone",
    "NumMentions",
    "NumSources",
    "NumArticles"
]

for column in numeric_columns:

    iran_events[column] = pd.to_numeric(
        iran_events[column],
        errors="coerce"
    )


# ==========================================
# DAILY AGGREGATION
# ==========================================

daily = iran_events.groupby("date").agg(

    event_count=(
        "GLOBALEVENTID",
        "count"
    ),

    avg_goldstein=(
        "GoldsteinScale",
        "mean"
    ),

    avg_tone=(
        "AvgTone",
        "mean"
    ),

    total_mentions=(
        "NumMentions",
        "sum"
    ),

    total_sources=(
        "NumSources",
        "sum"
    ),

    total_articles=(
        "NumArticles",
        "sum"
    )

).reset_index()


# ==========================================
# SORT
# ==========================================

daily = daily.sort_values("date")


# ==========================================
# DISPLAY
# ==========================================

print("\n==========================================")
print("       IRAN DAILY EVENT DATA")
print("==========================================")

print(
    daily.to_string(index=False)
)


# ==========================================
# SAVE
# ==========================================

daily.to_csv(
    "historical_events.csv",
    index=False
)

print("\nSaved:")
print("historical_events.csv")