# AI-Driven Energy Supply Chain Risk Dashboard

This is a current-risk dashboard for India’s oil-supply exposure in an Iran / Strait of Hormuz disruption context. It calculates and explains a current composite score from local GDELT-derived data. It does **not** predict future risk.

## Run it

Copy this folder into the existing codebase, alongside these files:

- `iran_events.csv`
- `gdelt_sentiment.csv`
- `historical_events.csv`

Install the dashboard dependencies once:

```powershell
py -m pip install -r requirements.txt
```

Then start the dashboard with one command:

```powershell
py -m streamlit run app.py
```

If the CSVs are kept elsewhere, enter their folder path in the dashboard sidebar.

## Data sources

- `iran_events.csv`: Iran-related GDELT Events records, including `GoldsteinScale`, `AvgTone`, mentions, and CAMEO event codes.
- `gdelt_sentiment.csv`: locally collected energy/logistics articles with VADER scores.
- `historical_events.csv`: daily Iran-related GDELT event aggregates for the historical trend.

The app does not fetch data at runtime. Refreshing source data is deliberately separate from viewing the dashboard.

## Current composite methodology

All component scores are expressed on a 0–100 risk scale, where higher means more risk.

1. Goldstein component: `(10 - GoldsteinScale) / 20`
2. AvgTone component: `(100 - AvgTone) / 200`, clipped only to the resulting 0–1 range.
3. GDELT Event Risk: `0.60 × Goldstein component + 0.40 × AvgTone component`
4. VADER Sentiment Risk: `(1 - compound_sentiment) / 2`
5. Composite Risk: `0.60 × GDELT Event Risk + 0.40 × VADER Sentiment Risk`

Events are weighted by `NumMentions` when calculating the current GDELT Event Risk. Categories are LOW below 25, MEDIUM from 25 to below 50, and HIGH at 50 or above. With the checked-in source data, the corrected current score is **52.49 / 100 (HIGH)**. This is 2.49 points above the HIGH boundary, so it should be described as a high but near-threshold reading.

### Method correction

Earlier scripts clipped `AvgTone` to ±10 before normalization. That was a defect: it collapsed materially different tone values (for example, −40 and −10) into the same risk input. The dashboard corrects this by normalizing across GDELT AvgTone’s full ±100 range. The earlier 57.82 score came from the defective clipping; the corrected data produces 52.49.

The historical chart uses daily GDELT Event aggregates. Since historical article-level VADER scores are unavailable, its secondary sentiment series is explicitly labeled as an AvgTone proxy; it is not represented as VADER sentiment.

## Experimental ML: evaluated, not deployed

The project tested whether historical features could predict next-day risk. The available data did not support a model that beat simple baselines:

| Task | Baseline | Tested model | Dashboard use |
| --- | --- | --- | --- |
| Risk-direction classification | Majority baseline: 55.56% accuracy | Logistic Regression: 46.15% | Not deployed |
| Next-day risk regression | Naive persistence: 1.32 MAE | Linear Regression: 2.39 MAE | Not deployed |

This negative result is retained as evidence of evaluation rigor. The live dashboard only calculates and explains the current score.

## Limitations

- The score reflects the supplied event and article data, not a live operational disruption measure.
- GDELT event coding and media tone are imperfect proxies for physical supply disruption.
- A risk score is a decision-support indicator, not a forecast, causal estimate, or trade recommendation.
