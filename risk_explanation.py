import pandas as pd

# ============================================================
# GENERAL GEOPOLITICAL RISK EXPLANATION
# ============================================================

print("Loading risk data...")

# Load the latest risk data
df = pd.read_csv("risk_data.csv")

# Convert date
df["date"] = pd.to_datetime(df["date"])

# Sort chronologically
df = df.sort_values("date").reset_index(drop=True)

# Latest available record
latest = df.iloc[-1]

# Previous available record
previous = df.iloc[-2]


# ============================================================
# COUNTRY / REGION
# ============================================================

# Current example/source.
# Change these values when adding another geopolitical situation.
country = "Iran"
region = "Middle East"


# ============================================================
# RISK SCORE
# ============================================================

risk_score = latest["risk_score"]

if risk_score >= 70:
    category = "HIGH"
elif risk_score >= 40:
    category = "MEDIUM"
else:
    category = "LOW"


# ============================================================
# COMPONENTS
# ============================================================

event_risk = latest["event_risk"]
sentiment_risk = latest["sentiment_risk"]


# ============================================================
# CURRENT CONDITIONS
# ============================================================

event_count = latest["event_count"]
total_mentions = latest["total_mentions"]
total_sources = latest["total_sources"]
total_articles = latest["total_articles"]

avg_goldstein = latest["avg_goldstein"]
avg_tone = latest["avg_tone"]


# ============================================================
# CHANGES
# ============================================================

event_count_change = event_count - previous["event_count"]
mentions_change = total_mentions - previous["total_mentions"]
goldstein_change = avg_goldstein - previous["avg_goldstein"]
tone_change = avg_tone - previous["avg_tone"]


# ============================================================
# OUTPUT
# ============================================================

print()
print("=" * 46)
print("       GEOPOLITICAL RISK MONITOR")
print("=" * 46)

print()
print(f"Date              : {latest['date'].date()}")
print(f"Country / Entity  : {country}")
print(f"Region            : {region}")

print()
print("-" * 46)
print("              OVERALL RISK")
print("-" * 46)

print(f"Risk Score        : {risk_score:.2f} / 100")
print(f"Category          : {category}")


print()
print("-" * 46)
print("             SCORE COMPONENTS")
print("-" * 46)

print(f"GDELT Event Risk  : {event_risk:.2f} / 100 (60%)")
print(f"Sentiment Risk    : {sentiment_risk:.2f} / 100 (40%)")


print()
print("-" * 46)
print("            CURRENT CONDITIONS")
print("-" * 46)

print(f"Event Count       : {event_count:.0f}")
print(f"Total Mentions    : {total_mentions:.0f}")
print(f"Total Sources     : {total_sources:.0f}")
print(f"Total Articles    : {total_articles:.0f}")
print(f"Average Goldstein : {avg_goldstein:.2f}")
print(f"Average Tone      : {avg_tone:.2f}")


print()
print("-" * 46)
print("         CHANGES FROM PREVIOUS DAY")
print("-" * 46)

print(f"Event Count Change : {event_count_change:+.0f}")
print(f"Mentions Change    : {mentions_change:+.0f}")
print(f"Goldstein Change   : {goldstein_change:+.2f}")
print(f"Tone Change        : {tone_change:+.2f}")


# ============================================================
# INTERPRETATION
# ============================================================

print()
print("-" * 46)
print("           RISK INTERPRETATION")
print("-" * 46)

if avg_goldstein < 0:
    print(
        "• Average Goldstein score is negative, "
        "indicating conflict-oriented event activity."
    )
else:
    print(
        "• Average Goldstein score is positive, "
        "indicating relatively cooperative event activity."
    )


if avg_tone < 0:
    print("• Average media tone is negative.")
else:
    print("• Average media tone is positive.")


if event_count_change > 0:
    print(
        f"• Event activity increased by "
        f"{event_count_change:.0f} events compared with "
        "the previous available day."
    )
elif event_count_change < 0:
    print(
        f"• Event activity decreased by "
        f"{abs(event_count_change):.0f} events compared with "
        "the previous available day."
    )
else:
    print("• Event activity remained unchanged.")


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
    print("• Media mentions remained unchanged.")


print()
print("=" * 46)
print("             END OF ANALYSIS")
print("=" * 46)