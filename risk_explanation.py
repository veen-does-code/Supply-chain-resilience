import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

GDELT_WEIGHT = 0.60
SENTIMENT_WEIGHT = 0.40

# Your current VADER result
SENTIMENT_RISK = 57.14


# ============================================================
# LOAD DATA
# ============================================================

print("Loading risk data...")

event_df = pd.read_csv("gdelt_event_risk.csv")
historical_df = pd.read_csv("historical_events.csv")


# ============================================================
# CALCULATE GDELT EVENT RISK
# ============================================================

gdelt_risk = event_df["event_risk"].mean() * 100


# ============================================================
# COMPOSITE RISK
# ============================================================

final_risk = (
    GDELT_WEIGHT * gdelt_risk
    + SENTIMENT_WEIGHT * SENTIMENT_RISK
)


# ============================================================
# RISK CATEGORY
# ============================================================

if final_risk < 33.33:
    category = "LOW"

elif final_risk < 66.67:
    category = "MEDIUM"

else:
    category = "HIGH"


# ============================================================
# PREPARE HISTORICAL DATA
# ============================================================

historical_df["date"] = pd.to_datetime(
    historical_df["date"]
)

historical_df = historical_df.sort_values(
    "date"
).reset_index(drop=True)


# Latest available day
latest = historical_df.iloc[-1]

# Previous available day
previous = historical_df.iloc[-2]


# ============================================================
# CURRENT DATA
# ============================================================

current_date = latest["date"].date()

event_count = latest["event_count"]

avg_goldstein = latest["avg_goldstein"]

avg_tone = latest["avg_tone"]

total_mentions = latest["total_mentions"]

total_sources = latest["total_sources"]

total_articles = latest["total_articles"]


# ============================================================
# CHANGES
# ============================================================

event_change = (
    latest["event_count"]
    - previous["event_count"]
)

goldstein_change = (
    latest["avg_goldstein"]
    - previous["avg_goldstein"]
)

tone_change = (
    latest["avg_tone"]
    - previous["avg_tone"]
)

mentions_change = (
    latest["total_mentions"]
    - previous["total_mentions"]
)


# ============================================================
# DISPLAY
# ============================================================

print()
print("==============================================")
print("          IRAN RISK EXPLANATION")
print("==============================================")

print()

print(f"Date: {current_date}")


# ============================================================
# FINAL RISK
# ============================================================

print()
print("----------------------------------------------")
print("               FINAL RISK")
print("----------------------------------------------")

print(f"Risk Score : {final_risk:.2f} / 100")
print(f"Category   : {category}")


# ============================================================
# SCORE COMPONENTS
# ============================================================

print()
print("----------------------------------------------")
print("             SCORE COMPONENTS")
print("----------------------------------------------")

print(
    f"GDELT Event Risk      : "
    f"{gdelt_risk:.2f} / 100 "
    f"({GDELT_WEIGHT * 100:.0f}%)"
)

print(
    f"VADER Sentiment Risk  : "
    f"{SENTIMENT_RISK:.2f} / 100 "
    f"({SENTIMENT_WEIGHT * 100:.0f}%)"
)


# ============================================================
# CURRENT CONDITIONS
# ============================================================

print()
print("----------------------------------------------")
print("             CURRENT CONDITIONS")
print("----------------------------------------------")

print(
    f"Event Count           : "
    f"{event_count:.0f}"
)

print(
    f"Total Mentions        : "
    f"{total_mentions:.0f}"
)

print(
    f"Total Sources         : "
    f"{total_sources:.0f}"
)

print(
    f"Total Articles        : "
    f"{total_articles:.0f}"
)

print(
    f"Average Goldstein     : "
    f"{avg_goldstein:.2f}"
)

print(
    f"Average Tone          : "
    f"{avg_tone:.2f}"
)


# ============================================================
# CHANGES FROM PREVIOUS DAY
# ============================================================

print()
print("----------------------------------------------")
print("          CHANGES FROM PREVIOUS DAY")
print("----------------------------------------------")

print(
    f"Event Count Change    : "
    f"{event_change:+.0f}"
)

print(
    f"Mentions Change       : "
    f"{mentions_change:+.0f}"
)

print(
    f"Goldstein Change      : "
    f"{goldstein_change:+.2f}"
)

print(
    f"Tone Change           : "
    f"{tone_change:+.2f}"
)


# ============================================================
# RISK INTERPRETATION
# ============================================================

print()
print("----------------------------------------------")
print("             RISK INTERPRETATION")
print("----------------------------------------------")


# Goldstein interpretation
if avg_goldstein < 0:

    print(
        "• Average Goldstein score is negative, "
        "indicating conflict-oriented event activity."
    )

else:

    print(
        "• Average Goldstein score is positive, "
        "indicating less conflict-oriented event activity."
    )


# Tone interpretation
if avg_tone < 0:

    print(
        "• Average media tone is negative."
    )

else:

    print(
        "• Average media tone is positive."
    )


# Event activity
if event_change > 0:

    print(
        f"• Event activity increased by "
        f"{event_change:.0f} events compared with "
        f"the previous available day."
    )

elif event_change < 0:

    print(
        f"• Event activity decreased by "
        f"{abs(event_change):.0f} events compared with "
        f"the previous available day."
    )

else:

    print(
        "• Event activity remained unchanged."
    )


# Mentions
if mentions_change > 0:

    print(
        f"• Media mentions increased by "
        f"{mentions_change:.0f}."
    )

elif mentions_change < 0:

    print(
        f"• Media mentions decreased by "
        f"{abs(mentions_change):.0f}."
    )

else:

    print(
        "• Media mentions remained unchanged."
    )


# ============================================================
# END
# ============================================================

print()
print("==============================================")
print("             END OF ANALYSIS")
print("==============================================")