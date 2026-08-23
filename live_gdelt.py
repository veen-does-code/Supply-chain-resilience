"""Reliable live GDELT access with persistent, visible fallbacks.

Full technical exceptions are logged for debugging; callers only receive short
human-readable messages suitable for the dashboard.
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


def _status(source: str, fetched_at: str, message: str, export_url: str = "") -> dict[str, str]:
    return {"source": source, "fetched_at": fetched_at, "message": message, "export_url": export_url}


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
    return events, export_url


def _save_event_cache(events: pd.DataFrame, export_url: str) -> None:
    events.to_pickle(_cache_path("events.pkl"))
    _write_metadata("events.json", fetched_at=_now(), export_url=export_url)


def _load_event_cache() -> tuple[pd.DataFrame, dict[str, str]] | None:
    path = CACHE_DIRECTORY / "events.pkl"
    if not path.exists():
        return None
    try:
        return pd.read_pickle(path), _read_metadata("events.json")
    except Exception:
        LOGGER.exception("Could not load cached Event data")
        return None


def _legacy_event_snapshot() -> tuple[pd.DataFrame, dict[str, str]] | None:
    path = Path(__file__).with_name("iran_events.csv")
    if not path.exists():
        return None
    try:
        return pd.read_csv(path), _status("local", datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(), "Showing the bundled Hormuz/Iran snapshot; live data is unavailable.")
    except Exception:
        LOGGER.exception("Could not load legacy event fallback")
        return None


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
        return events, _status("cache", metadata.get("fetched_at", "an unknown time"), "Showing cached Event data; live refresh is unavailable.", metadata.get("export_url", ""))
    local = _legacy_event_snapshot()
    if local:
        return local
    raise LiveDataError("Live data is unavailable and no cached snapshot is stored yet.")


def filter_events(events: pd.DataFrame, chokepoint: Chokepoint) -> pd.DataFrame:
    """Filter events by the chokepoint's documented country codes and terms."""
    codes = set(chokepoint.country_codes)
    terms = "|".join(chokepoint.search_terms)
    actor_one = events["Actor1CountryCode"].fillna("").str.upper().isin(codes)
    actor_two = events["Actor2CountryCode"].fillna("").str.upper().isin(codes)
    names = events["Actor1Name"].fillna("").str.contains(terms, case=False, regex=True) | events["Actor2Name"].fillna("").str.contains(terms, case=False, regex=True)
    return events[actor_one | actor_two | names].copy()


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
    articles["sentiment"] = pd.cut(scores, bins=[-float("inf"), -0.05, 0.05, float("inf")], labels=["Negative", "Neutral", "Positive"], include_lowest=True).astype(str)
    for column in ("url", "seendate", "domain", "language", "sourcecountry"):
        if column not in articles:
            articles[column] = None
    return articles[ARTICLE_COLUMNS]


def _article_cache_name(chokepoint: Chokepoint) -> str:
    return f"articles_{chokepoint.key}.csv"


def _load_article_cache(chokepoint: Chokepoint) -> tuple[pd.DataFrame, dict[str, str]] | None:
    path = CACHE_DIRECTORY / _article_cache_name(chokepoint)
    if not path.exists():
        return None
    try:
        return pd.read_csv(path), _read_metadata(f"articles_{chokepoint.key}.json")
    except Exception:
        LOGGER.exception("Could not load cached articles for %s", chokepoint.key)
        return None


def _legacy_article_snapshot(chokepoint: Chokepoint) -> tuple[pd.DataFrame, dict[str, str]] | None:
    if chokepoint.key != "hormuz":
        return None
    path = Path(__file__).with_name("gdelt_sentiment.csv")
    if not path.exists():
        return None
    try:
        return pd.read_csv(path), _status("local", datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(), "Showing the bundled Hormuz/Iran article snapshot; live data is unavailable.")
    except Exception:
        LOGGER.exception("Could not load legacy article fallback")
        return None


def load_articles(chokepoint: Chokepoint, force_offline: bool = False) -> tuple[pd.DataFrame, dict[str, str]]:
    """Return live articles, with per-chokepoint cache and local fallback."""
    if not force_offline:
        try:
            articles = _fetch_live_articles(chokepoint)
            articles.to_csv(_cache_path(_article_cache_name(chokepoint)), index=False)
            metadata = _status("live", _now(), "Live GDELT article data loaded.")
            _write_metadata(f"articles_{chokepoint.key}.json", **metadata)
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
    raise LiveDataError(f"No cached article data is available for {chokepoint.name}.")
