# Energy Supply Route Risk Monitor

A route-based, current-risk dashboard for energy-shipping corridors, built on
live GDELT event and news data. Built for Problem Statement 1
(AI-Driven Energy Supply Chain Resilience for Import-Dependent Economies).

## What this does — and doesn't — do

- It calculates a **current** risk score (0–100) for a modeled shipping
  route, based on real-time geopolitical event data and news sentiment.
- It does **not** predict future risk. A separate, honestly-documented
  experiment tested whether historical patterns could predict next-day risk
  direction/value; the tested models did not outperform simple baselines, so
  no predictive model is deployed here (see "Method" tab in the app, or the
  Experiment Record section below).
- Routes are modeled through a **fixed table of major maritime chokepoints**
  (Strait of Hormuz, Suez Canal, Strait of Malacca, Bab-el-Mandeb, Bosphorus,
  Strait of Gibraltar, Panama Canal, Cape of Good Hope), not real-time vessel
  tracking or precise geospatial pathfinding. This is a deliberate,
  documented simplification appropriate for a hackathon timeline — see
  `routes.py`.

## How the score is calculated

For each chokepoint on the modeled route:

- **Event risk** = 60% × `goldstein_risk_component` + 40% × `tone_risk`,
  computed per GDELT event and aggregated weighted by `NumMentions`.
  - `goldstein_risk_component` normalizes `GoldsteinScale` (theoretical
    event-type conflict/cooperation intensity, range −10..+10) to a 0..1
    risk value.
  - `tone_risk` normalizes `AvgTone` (average tone of documents mentioning
    the event) over its **full −100..+100 range**.
- **Sentiment risk** = derived from VADER compound sentiment scores on
  recent news articles matching the chokepoint's search terms.
- **Chokepoint composite** = 60% Event risk + 40% Sentiment risk.
- **Route score** = equal-weight average of composite scores across every
  chokepoint on the route that has usable data. A chokepoint with no
  matching events/articles in the current snapshot is **excluded**, not
  scored as zero — this is shown explicitly in the UI.
- **Category**: LOW (<25), MEDIUM (<50), HIGH (≥50).

### Correction record

An earlier version of this pipeline clipped `AvgTone` to ±10 before
normalizing, which collapsed distinct tone values (e.g. −40 and −10 both
mapped to the same risk). That reference calculation produced a composite of
**57.82/100**. The corrected version in this codebase normalizes over the
real ±100 range, producing **52.49/100** for the same underlying Iran/Hormuz
data — still HIGH, but a materially different, more accurate number. If any
slides, pitch notes, or prior README versions still cite 57.82, update them
to 52.49.

## Experiment record: why there's no predictive model

A historical daily dataset (~64 observations) was built with engineered
features (article sentiment stats, event counts, Goldstein/tone averages,
trend deltas). Logistic Regression and Linear Regression were tested against
simple baselines to predict next-day risk direction/value:

| Task | Simple baseline | Tested model |
|---|---|---|
| Risk-direction classification | Majority baseline: 55.56% accuracy | Logistic Regression: 46.15% accuracy |
| Next-day risk regression | Naive persistence: 1.32 MAE | Linear Regression: 2.39 MAE |

Neither model beat its baseline — expected, given how little historical data
was available relative to the number of features. Rather than deploy an
unvalidated predictive claim, this result is shown transparently in the
dashboard's Method tab, framed as: *"we tested whether historical patterns
could predict next-day risk; they did not outperform simple baselines, so
prediction is not used here."*

## Adaptive Procurement Orchestrator

The "Procurement Orchestrator" tab implements the brief's illustrative
direction: *"ranks alternative crude sources and logistics routes for
procurement teams to act on within hours."* For the currently selected
destination, it finds every other origin region with a modeled route to
that destination (via the same fixed rules table used for the main route),
scores each alternative with the **identical** scoring pipeline used for
the primary route, and ranks them by current modeled risk — surfacing
whether a lower-risk sourcing alternative exists right now.

This reuses `route_scoring.score_route()` for every candidate, so an
alternative is never scored differently than the primary route would be if
you'd picked it directly. Alternatives with no usable event/article data in
the current snapshot are skipped and noted, not silently treated as
risk-free. The tab is explicit that it ranks **modeled current risk only** —
not cost, contract lead time, refinery compatibility, or real-world
feasibility of switching suppliers.

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit dashboard — route selection, scoring, and display |
| `live_gdelt.py` | Live GDELT fetching (HTTPS, retries, connectivity check), with cache and legacy-snapshot fallbacks |
| `risk_model.py` | Risk normalization and composite scoring formula |
| `routes.py` | Chokepoint lookup table, the region-pair → chokepoint-route heuristic, and alternative-origin lookup |
| `route_scoring.py` | Shared per-route scoring used by both the primary route view and the Procurement Orchestrator |
| `requirements.txt` | Python dependencies |

### Fix record: legacy Iran snapshot scoping

`data_loader.py` (present in this repo but not wired into `app.py`) confirms
`iran_events.csv`'s real required columns are `EventCode, EventRootCode,
GoldsteinScale, AvgTone, NumMentions` — it does **not** carry per-row
`Actor1CountryCode`/`Actor2CountryCode`/`Actor1Name`/`Actor2Name` columns,
because the file was already pre-filtered to Iran/Hormuz events when it was
created. An earlier version of `live_gdelt.py` required those actor/country
columns before accepting any fallback snapshot, which meant the bundled
Iran snapshot silently failed as a fallback even though it's valid data.
This is fixed: the legacy snapshot is now flagged with `scope:
"hormuz_only"` and used wholesale for the Hormuz chokepoint via
`events_for_chokepoint()`, instead of being run through the generic
country-code filter it was never able to satisfy.

## Data reliability

Live data is fetched fresh on each explicit refresh (or app load), with this
fallback order if live fetching fails:

1. **Cache** — the most recent successfully-fetched data, saved locally
   after every successful live fetch.
2. **Legacy snapshot** — the bundled `iran_events.csv` / `gdelt_sentiment.csv`
   files, if present, for a Hormuz-only route. These are validated against
   the expected schema before use; a mismatched file is treated as
   unavailable (logged, not surfaced as a crash) so the app degrades
   gracefully rather than failing on a raw exception.

A manual "Use offline/cached data" toggle is available in the sidebar for
demoing on unreliable venue wifi without gambling on a live fetch mid-demo.

No raw exception text or stack traces are ever shown in the UI — failures
are logged internally and surfaced as short, calm status messages.

## Known limitations

- **Trend tab only accumulates within one browser session.** Refreshing live
  data adds an observation to the trend graph, but there is no multi-day
  historical trend for the generalized route view (the earlier Iran-only
  version had a 66-day historical trend from `historical_events.py`; that
  data source hasn't been re-integrated into the route-based architecture).
  If you want a real historical trend, the fastest path is pulling several
  days of Goldstein/AvgTone directly from GDELT's BigQuery public dataset,
  rather than re-scraping daily articles.
- **The chokepoint route table covers a fixed set of region pairs.** An
  unsupported pair shows a clear message rather than guessing; a supported
  pair with no major chokepoint (e.g. trans-Pacific) also shows a clear,
  distinct message rather than being confused with "unsupported."
- **Legacy fallback data only covers the Hormuz chokepoint.** Other
  chokepoints have no offline fallback if live data is unavailable and no
  cache exists yet from a prior successful fetch.

## Running it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Requires Python 3.10+ (uses `X | None` type hints via
`from __future__ import annotations`, compatible back to 3.9 with that
import present).
