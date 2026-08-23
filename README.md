# Live Energy Supply Route Risk Dashboard

This Streamlit app calculates and explains **current** geopolitical/logistics risk for selected energy-shipping corridors. It uses live GDELT signals for the major chokepoints on an illustrative route. It does **not** predict future risk.

## Run

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

No local CSV is required at runtime. The app fetches the newest GDELT Event 15-minute export and recent GDELT DOC articles when the route is loaded or refreshed.

## Route model

The dashboard supports the following major chokepoints:

| Chokepoint | Monitoring countries / regions |
| --- | --- |
| Strait of Hormuz | Iran, Oman, United Arab Emirates |
| Bab-el-Mandeb | Yemen, Djibouti, Eritrea |
| Suez Canal | Egypt |
| Strait of Malacca | Indonesia, Malaysia, Singapore |
| Turkish Straits / Bosphorus | Turkey |
| Strait of Gibraltar | Spain, Morocco |
| Panama Canal | Panama |
| Cape of Good Hope | South Africa |

The route is chosen from a transparent fixed rules table. For example, Persian Gulf → Europe is modeled as Strait of Hormuz → Bab-el-Mandeb → Suez Canal. This is an illustrative choke-point heuristic, **not** vessel tracking, real-time routing, or precise geospatial pathfinding. It must not be used as a certified shipping-route calculation.

## Live data and resilience

- Events: the app reads GDELT `lastupdate.txt`, downloads the newest `.export.CSV.zip` Event file, then filters it using each chokepoint’s country codes and place terms.
- Articles: the app queries GDELT DOC 2.0 for recent, energy/logistics-related articles associated with each chokepoint and runs VADER on article titles.
- Cache: Event and article responses are cached for five minutes. **Refresh live data** deliberately requests fresh responses.
- Failures: a chokepoint with missing events, missing articles, or a fetch/parse failure is explicitly listed as unavailable and excluded from the route average. It is never silently assigned a zero.
- Trend: the chart records live route observations made during the current browser session. It starts with the first successful observation and grows as the user refreshes. It does not present the prior Iran-only CSV history as route-wide live history.

GDELT Event exports update on a near-real-time 15-minute cycle. DOC article retrieval uses a recent 24-hour search window. GDELT availability, media coverage, coding and API limits can all affect the result.

## Risk methodology

All scores are 0–100, with higher values indicating greater current risk.

1. Goldstein risk component: `(10 - GoldsteinScale) / 20`
2. AvgTone risk component: `(100 - AvgTone) / 200`, bounded to 0–1 only after using the full ±100 range.
3. GDELT Event Risk: `0.60 × Goldstein component + 0.40 × AvgTone component`, weighted by `NumMentions` within that chokepoint.
4. VADER Sentiment Risk: `(1 - compound_sentiment) / 2`
5. Chokepoint Composite: `0.60 × GDELT Event Risk + 0.40 × VADER Sentiment Risk`
6. Route Risk: equal-weight average of every chokepoint with usable live event and article data.

Equal route weights make the aggregation easy to explain and prevent GDELT record volume at one chokepoint from overwhelming the others. The model’s event calculation still uses mention weighting within each chokepoint.

Categories are LOW below 25, MEDIUM from 25 to below 50, and HIGH at 50 or above.

### Normalization correction

Earlier project scripts clipped `AvgTone` to ±10 before normalization. That was a defect because it collapsed materially different tone values. The app uses the full ±100 range and does not reproduce the earlier 57.82 score produced by that clipping bug.

## Experimental ML: evaluated, not deployed

The original Iran-only experiment tested next-day prediction on historical data. It did not beat simple baselines, so it is retained for rigor and is not part of any live score.

| Task | Baseline | Tested model | Live use |
| --- | --- | --- | --- |
| Risk-direction classification | Majority baseline: 55.56% accuracy | Logistic Regression: 46.15% | Not deployed |
| Next-day risk regression | Naive persistence: 1.32 MAE | Linear Regression: 2.39 MAE | Not deployed |

## Limitations

- This is a current news/event indicator, not a forecast or operational disruption measurement.
- Fixed chokepoint rules simplify complex shipping paths and do not account for vessel position, insurance, weather, port congestion, sanctions compliance, or alternative routing.
- GDELT’s event coding and media tone are imperfect proxies for physical supply disruption.
