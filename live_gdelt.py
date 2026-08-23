"""Reliable live GDELT access with persistent, visible fallbacks.

Full technical exceptions are logged for debugging; callers only receive short
human-readable messages suitable for the dashboard.

Data can arrive from four places: a fresh live fetch, a locally pickled/CSV
cache from a prior successful fetch, or a bundled legacy snapshot file left
over from an earlier version of this project (iran_events.csv /
gdelt_sentiment.csv). Only the live path is guaranteed to match the current
column schema exactly, so every other path is passed through
_normalise_event_frame / _normalise_article_frame before use. If a snapshot
is missing a column that can't be reasonably inferred, normalisation returns
None and the caller falls through to the next option -- a schema mismatch in
an old file degrades gracefully instead of crashing the dashboard with a raw
KeyError later in the UI.

Schema note: per data_loader.py's validated column list, iran_events.csv was
pre-filtered to Iran/Hormuz events at creation time and does NOT carry
per-row actor/country columns. It is therefore used wholesale for the Hormuz
chokepoint only (see the "scope" field on its status, and
events_for_chokepoint below) rather than being run through the normal
country-code filter used for live/cached data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import json
import logging
from pathlib import Path
from typing import Any
import zipfile

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from routes import Chokepoint


LOGGER = logging.getLogger(__name__)
LAST_UPDATE_URL = "https://data.gdeltproject.org/gdeltv2/lastupdate.txt"
DOC_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
CONNECT_TIMEOUT_SECONDS = 5
READ_TIMEOUT_SECONDS = 8
CACHE_DIRECTORY = Path(__file__).with_name(".gdelt_cache")

EVENT_COLUMNS = [
    "GLOBALEVENTID", "SQLDATE", "Actor1Name", "Actor1CountryCode", "Actor2Name", "Actor2CountryCode",
    "EventCode", "EventBaseCode", "EventRootCode", "QuadClass", "GoldsteinScale", "NumMentions",
    "NumSources", "NumArticles", "AvgTone", "SOURCEURL",
]
EVENT_USECOLS = [0, 1, 6, 7, 16, 17, 26, 27, 28, 29, 30, 31, 32, 33, 34, 57]
ARTICLE_COLUMNS = ["title", "url", "seendate", "domain", "language", "sourcecountry", "sentiment", "sentiment_score"]

# Columns a fallback file MUST have (directly or via an alias below) or the
# snapshot is treated as unusable rather than risking a crash downstream.
# Actor/country columns are deliberately NOT required here: the bundled
# iran_events.csv legitimately doesn't carry them (see module docstring).
# Chokepoint scoping for that file is handled by events_for_chokepoint()
# using the "scope" status field instead of per-row country matching.
REQUIRED_EVENT_COLUMNS = ("GoldsteinScale", "AvgTone", "NumMentions")
REQUIRED_ARTICLE_COLUMNS = ("title", "sentiment_score")

# Best-effort aliases for older/differently-named columns in legacy files.
ARTICLE_COLUMN_ALIASES = {
    "sentiment_score": ("sentiment_score", "compound", "vader_compound", "vader_score", "polarity"),
    "seendate": ("seendate", "date", "published", "pub_date"),
    "sentiment": ("sentiment", "sentiment_label", "label"),
    "url": ("url", "link", "source_url", "sourceurl"),
    "domain": ("domain", "source", "source_domain"),
}


class LiveDataError(RuntimeError):
    """A concise dashboard-safe message after all fallback options fail."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session() -> requests.Session:
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=0.4,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session


def _request(session: requests.Session, url: str, **kwargs: Any) -> requests.Response:
    """Always use HTTPS and a short connect/read timeout pair."""
    secure_url = url.replace("http://", "https://", 1)
    return session.get(secure_url, timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS), **kwargs)


def _cache_path(name: str) -> Path:
    CACHE_DIRECTORY.mkdir(exist_ok=True)
    return CACHE_DIRECTORY / name


def _write_metadata(name: str, **values: str) -> None:
    _cache_path(name).write_text(json.dumps(values, indent=2), encoding="utf-8")


def _read_metadata(name: str) -> dict[str, str]:
    path = CACHE_DIRECTORY / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        LOGGER.exception("Could not read cached GDELT metadata")
        return {}


def _status(source: str, fetched_at: str, message: str, export_url: str = "", scope: str = "") -> dict[str, str]:
    return {"source": source, "fetched_at": fetched_at, "message": message, "export_url": export_url, "scope": scope}


def _normalise_event_frame(df: pd.DataFrame) -> pd.DataFrame | None:
    """Align any event dataframe (live, cached, or legacy) to EVENT_COLUMNS.

    Returns None if a required column can't be found, so the caller can fall
    through to the next data source instead of crashing later. Actor/country
    columns are filled with None if absent rather than required -- see the
    module docstring for why (the bundled legacy snapshot legitimately lacks
    them).
    """
    frame = df.copy()
    frame.columns = [str(column).strip() for column in frame.columns]
    missing_required = [column for column in REQUIRED_EVENT_COLUMNS if column not in frame.columns]
    if missing_required:
        LOGGER.warning("Event snapshot missing required columns %s; treating as unusable.", missing_required)
        return None
    for column in EVENT_COLUMNS:
        if column not in frame.columns:
            frame[column] = None
    frame["GoldsteinScale"] = pd.to_numeric(frame["GoldsteinScale"], errors="coerce")
    frame["AvgTone"] = pd.to_numeric(frame["AvgTone"], errors="coerce")
    frame["NumMentions"] = pd.to_numeric(frame["NumMentions"], errors="coerce")
    return frame[EVENT_COLUMNS]


def _normalise_article_frame(df: pd.DataFrame) -> pd.DataFrame | None:
    """Align any article dataframe (live, cached, or legacy) to ARTICLE_COLUMNS.

    Applies best-effort column aliasing for legacy files, then returns None
    if a required column still can't be found -- same fall-through contract
    as _normalise_event_frame.
    """
    frame = df.copy()
    frame.columns = [str(column).strip() for column in frame.columns]
    for target, aliases in ARTICLE_COLUMN_ALIASES.items():
        if target in frame.columns:
            continue
        match = next((alias for alias in aliases if alias in frame.columns), None)
        if match:
            frame[target] = frame[match]
    missing_required = [column for column in REQUIRED_ARTICLE_COLUMNS if column not in frame.columns]
    if missing_required:
        LOGGER.warning("Article snapshot missing required columns %s; treating as unusable.", missing_required)
        return None
    frame["sentiment_score"] = pd.to_numeric(frame["sentiment_score"], errors="coerce")
    if "sentiment" not in frame.columns or frame["sentiment"].isna().all():
        frame["sentiment"] = pd.cut(
            frame["sentiment_score"],
            bins=[-float("inf"), -0.05, 0.05, float("inf")],
            labels=["Negative", "Neutral", "Positive"],
            include_lowest=True,
        ).astype(str)
    for column in ARTICLE_COLUMNS:
        if column not in frame.columns:
            frame[column] = None
    return frame[ARTICLE_COLUMNS]


def check_connectivity(session: requests.Session | None = None) -> bool:
    """Fast reachability check, preventing a slow export attempt on blocked Wi-Fi."""
    client = session or _session()
    try:
        response = client.get(LAST_UPDATE_URL, timeout=(CONNECT_TIMEOUT_SECONDS, CONNECT_TIMEOUT_SECONDS))
        response.raise_for_status()
        return bool(response.text.strip())
    except requests.RequestException:
        LOGGER.exception("GDELT connectivity self-check failed")
        return False


def _latest_event_export_url(session: requests.Session) -> str:
    response = _request(session, LAST_UPDATE_URL)
    response.raise_for_status()
    urls = [line.split()[-1] for line in response.text.splitlines() if line.strip()]
    event_urls = [url.replace("http://", "https://", 1) for url in urls if url.lower().endswith(".export.csv.zip")]
    if not event_urls:
        raise LiveDataError("The latest GDELT update did not include an Event export.")
    return event_urls[0]


def _fetch_live_events() -> tuple[pd.DataFrame, str]:
    session = _session()
    if not check_connectivity(session):
        raise LiveDataError("Live GDELT is not reachable on this network.")
    export_url = _latest_event_export_url(session)
    response = _request(session, export_url)
    response.raise_for_status()
    try:
        with zipfile.ZipFile(BytesIO(response.content)) as archive:
            with archive.open(archive.namelist()[0]) as stream:
                events = pd.read_csv(stream, sep="\t", header=None, names=EVENT_COLUMNS, usecols=EVENT_USECOLS, low_memory=False)
    except (zipfile.BadZipFile, IndexError, pd.errors.ParserError) as exc:
        LOGGER.exception("Could not parse live GDELT Event export")
        raise LiveDataError("The newest GDELT Event file could not be read.") from exc
    normalised = _normalise_event_frame(events)
    if normalised is None:
        raise LiveDataError("The newest GDELT Event file did not match the expected format.")
    return normalised, export_url


def _save_event_cache(events: pd.DataFrame, export_url: str) -> None:
    events.to_pickle(_cache_path("events.pkl"))
    _write_metadata("events.json", fetched_at=_now(), export_url=export_url)


def _load_event_cache() -> tuple[pd.DataFrame, dict[str, str]] | None:
    path = CACHE_DIRECTORY / "events.pkl"
    if not path.exists():
        return None
    try:
        events = pd.read_pickle(path)
    except Exception:
        LOGGER.exception("Could not load cached Event data")
        return None
    normalised = _normalise_event_frame(events)
    if normalised is None:
        return None
    return normalised, _read_metadata("events.json")


def _legacy_event_snapshot() -> tuple[pd.DataFrame, dict[str, str]] | None:
    """The bundled iran_events.csv -- pre-filtered to Iran/Hormuz at creation.

    It has no actor/country columns to filter by, so it is flagged with
    scope="hormuz_only" and used wholesale for the Hormuz chokepoint only by
    events_for_chokepoint(), never run through the generic country-code
    filter used for live/cached data.
    """
    path = Path(__file__).with_name("iran_events.csv")
    if not path.exists():
        return None
    try:
        raw = pd.read_csv(path)
    except Exception:
        LOGGER.exception("Could not read legacy event fallback")
        return None
    normalised = _normalise_event_frame(raw)
    if normalised is None:
        return None
    fetched_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    return normalised, _status(
        "local", fetched_at,
        "Showing the bundled Hormuz/Iran snapshot; live data is unavailable.",
        scope="hormuz_only",
    )


def load_event_data(force_offline: bool = False) -> tuple[pd.DataFrame, dict[str, str]]:
    """Return live events when possible, otherwise a cached or bundled snapshot."""
    if not force_offline:
        try:
            events, export_url = _fetch_live_events()
            _save_event_cache(events, export_url)
            return events, _status("live", _now(), "Live GDELT Event data loaded.", export_url)
        except (requests.RequestException, LiveDataError):
            LOGGER.exception("Live Event fetch failed; attempting fallback")
    cached = _load_event_cache()
    if cached:
        events, metadata = cached
        return events, _status(
            "cache", metadata.get("fetched_at", "an unknown time"),
            "Showing cached Event data; live refresh is unavailable.",
            metadata.get("export_url", ""),
        )
    local = _legacy_event_snapshot()
    if local:
        return local
    raise LiveDataError("Live data is unavailable and no compatible cached or local snapshot could be loaded.")


def filter_events(events: pd.DataFrame, chokepoint: Chokepoint) -> pd.DataFrame:
    """Filter events by the chokepoint's documented country codes and terms.

    Only meaningful for data that actually carries actor/country columns
    (live and cached data). Use events_for_chokepoint() as the general entry
    point -- it routes scoped legacy data correctly instead of calling this
    directly.
    """
    codes = set(chokepoint.country_codes)
    terms = "|".join(chokepoint.search_terms)
    actor_one = events["Actor1CountryCode"].fillna("").str.upper().isin(codes)
    actor_two = events["Actor2CountryCode"].fillna("").str.upper().isin(codes)
    names = events["Actor1Name"].fillna("").str.contains(terms, case=False, regex=True) | events["Actor2Name"].fillna("").str.contains(terms, case=False, regex=True)
    return events[actor_one | actor_two | names].copy()


def events_for_chokepoint(events: pd.DataFrame, chokepoint: Chokepoint, event_status: dict[str, str]) -> pd.DataFrame:
    """Select events relevant to a chokepoint, respecting the source's scope.

    Live and cached data cover many countries and are filtered by the
    chokepoint's country codes/search terms via filter_events(). The bundled
    legacy snapshot (scope == "hormuz_only") is pre-filtered to Iran/Hormuz
    and carries no country columns to filter by, so it is used wholesale for
    the Hormuz chokepoint only, and treated as empty (unavailable, not zero)
    for every other chokepoint.
    """
    if event_status.get("scope") == "hormuz_only":
        if chokepoint.key == "hormuz":
            return events.copy()
        return events.iloc[0:0].copy()
    return filter_events(events, chokepoint)


def _article_query(chokepoint: Chokepoint) -> str:
    places = " OR ".join(f'"{term}"' if " " in term else term for term in chokepoint.search_terms)
    return f"({places}) (oil OR crude OR tanker OR shipping OR energy OR port OR blockade OR sanctions) sourcelang:english"


def _fetch_live_articles(chokepoint: Chokepoint) -> pd.DataFrame:
    session = _session()
    response = _request(session, DOC_API_URL, params={"query": _article_query(chokepoint), "mode": "artlist", "format": "json", "maxrecords": 75, "timespan": "24h", "sort": "datedesc"})
    response.raise_for_status()
    try:
        articles = pd.DataFrame(response.json().get("articles", []))
    except ValueError as exc:
        LOGGER.exception("GDELT DOC returned non-JSON")
        raise LiveDataError("GDELT article data could not be read.") from exc
    if articles.empty or "title" not in articles:
        return pd.DataFrame(columns=ARTICLE_COLUMNS)
    scores = articles["title"].fillna("").map(lambda title: SentimentIntensityAnalyzer().polarity_scores(title)["compound"])
    articles["sentiment_score"] = scores
    normalised = _normalise_article_frame(articles)
    if normalised is None:
        raise LiveDataError("Live GDELT article data did not match the expected format.")
    return normalised


def _article_cache_name(chokepoint: Chokepoint) -> str:
    return f"articles_{chokepoint.key}.csv"


def _load_article_cache(chokepoint: Chokepoint) -> tuple[pd.DataFrame, dict[str, str]] | None:
    path = CACHE_DIRECTORY / _article_cache_name(chokepoint)
    if not path.exists():
        return None
    try:
        raw = pd.read_csv(path)
    except Exception:
        LOGGER.exception("Could not load cached articles for %s", chokepoint.key)
        return None
    normalised = _normalise_article_frame(raw)
    if normalised is None:
        return None
    return normalised, _read_metadata(f"articles_{chokepoint.key}.json")


def _legacy_article_snapshot(chokepoint: Chokepoint) -> tuple[pd.DataFrame, dict[str, str]] | None:
    if chokepoint.key != "hormuz":
        return None
    path = Path(__file__).with_name("gdelt_sentiment.csv")
    if not path.exists():
        return None
    try:
        raw = pd.read_csv(path)
    except Exception:
        LOGGER.exception("Could not load legacy article fallback")
        return None
    normalised = _normalise_article_frame(raw)
    if normalised is None:
        return None
    fetched_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    return normalised, _status("local", fetched_at, "Showing the bundled Hormuz/Iran article snapshot; live data is unavailable.")


def load_articles(chokepoint: Chokepoint, force_offline: bool = False) -> tuple[pd.DataFrame, dict[str, str]]:
    """Return live articles, with per-chokepoint cache and local fallback."""
    if not force_offline:
        try:
            articles = _fetch_live_articles(chokepoint)
            articles.to_csv(_cache_path(_article_cache_name(chokepoint)), index=False)
            metadata = _status("live", _now(), "Live GDELT article data loaded.")
            _write_metadata(f"articles_{chokepoint.key}.json", **{k: v for k, v in metadata.items() if k != "scope"})
            return articles, metadata
        except (requests.RequestException, LiveDataError):
            LOGGER.exception("Live article fetch failed for %s; attempting fallback", chokepoint.key)
    cached = _load_article_cache(chokepoint)
    if cached:
        articles, metadata = cached
        return articles, _status("cache", metadata.get("fetched_at", "an unknown time"), f"Showing cached articles for {chokepoint.name}; live refresh is unavailable.")
    local = _legacy_article_snapshot(chokepoint)
    if local:
        return local
    raise LiveDataError(f"No compatible cached or local article data is available for {chokepoint.name}.")
