"""Illustrative maritime chokepoint lookup and route heuristic.

This is deliberately not vessel tracking or geospatial pathfinding.  It makes
the route assumption visible and repeatable for a hackathon demonstration.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chokepoint:
    key: str
    name: str
    latitude: float
    longitude: float
    country_codes: tuple[str, ...]
    search_terms: tuple[str, ...]


CHOKEPOINTS = {
    "hormuz": Chokepoint("hormuz", "Strait of Hormuz", 26.57, 56.25, ("IRN", "OMN", "ARE"), ("Iran", "Oman", "United Arab Emirates", "Strait of Hormuz")),
    "bab_el_mandeb": Chokepoint("bab_el_mandeb", "Bab-el-Mandeb", 12.58, 43.33, ("YEM", "DJI", "ERI"), ("Yemen", "Djibouti", "Eritrea", "Bab-el-Mandeb", "Red Sea")),
    "suez": Chokepoint("suez", "Suez Canal", 30.44, 32.35, ("EGY",), ("Egypt", "Suez Canal")),
    "malacca": Chokepoint("malacca", "Strait of Malacca", 2.50, 101.00, ("IDN", "MYS", "SGP"), ("Indonesia", "Malaysia", "Singapore", "Strait of Malacca")),
    "bosphorus": Chokepoint("bosphorus", "Turkish Straits / Bosphorus", 41.12, 29.07, ("TUR",), ("Turkey", "Turkish Straits", "Bosphorus")),
    "gibraltar": Chokepoint("gibraltar", "Strait of Gibraltar", 35.98, -5.61, ("ESP", "MAR"), ("Spain", "Morocco", "Strait of Gibraltar")),
    "panama": Chokepoint("panama", "Panama Canal", 9.08, -79.68, ("PAN",), ("Panama", "Panama Canal")),
    "cape_good_hope": Chokepoint("cape_good_hope", "Cape of Good Hope", -34.36, 18.47, ("ZAF",), ("South Africa", "Cape of Good Hope")),
}

REGIONS = (
    "Persian Gulf",
    "Middle East",
    "South Asia",
    "Southeast Asia",
    "East Asia",
    "Europe",
    "Mediterranean",
    "North America East Coast",
    "North America West Coast",
    "West Africa",
)

# Each value is an ordered tuple of CHOKEPOINTS keys for that corridor.  An
# EMPTY tuple is a deliberate, documented statement that the corridor is
# open-ocean in this simplified model — that is NOT the same thing as an
# "unknown pair", which is represented by the pair being absent from this
# table entirely. route_for() below preserves that distinction.
_ROUTE_RULES: dict[tuple[str, str], tuple[str, ...]] = {
    ("Persian Gulf", "East Asia"): ("hormuz", "malacca"),
    ("Persian Gulf", "Southeast Asia"): ("hormuz", "malacca"),
    ("Persian Gulf", "South Asia"): ("hormuz",),
    ("Persian Gulf", "Europe"): ("hormuz", "bab_el_mandeb", "suez"),
    ("Persian Gulf", "Mediterranean"): ("hormuz", "bab_el_mandeb", "suez"),
    ("Persian Gulf", "North America East Coast"): ("hormuz", "bab_el_mandeb", "suez", "gibraltar"),
    ("Middle East", "East Asia"): ("hormuz", "malacca"),
    ("Middle East", "Southeast Asia"): ("hormuz", "malacca"),
    ("Middle East", "Europe"): ("hormuz", "bab_el_mandeb", "suez"),
    ("Europe", "East Asia"): ("suez", "bab_el_mandeb", "malacca"),
    ("Europe", "Southeast Asia"): ("suez", "bab_el_mandeb", "malacca"),
    ("Europe", "North America East Coast"): ("gibraltar",),
    ("Europe", "North America West Coast"): ("gibraltar", "panama"),
    ("East Asia", "North America West Coast"): (),
    ("East Asia", "North America East Coast"): ("panama",),
    ("Southeast Asia", "Europe"): ("malacca", "bab_el_mandeb", "suez"),
}

<<<<<<< HEAD

def route_for(start: str, end: str) -> list[Chokepoint] | None:
=======
ROUTE_RULES = {
    ("Persian Gulf", "East Asia"): ("hormuz", "malacca"),
    ("Persian Gulf", "Southeast Asia"): ("hormuz", "malacca"),
    ("Persian Gulf", "South Asia"): ("hormuz",),
    ("Persian Gulf", "Europe"): ("hormuz", "bab_el_mandeb", "suez"),
    ("Persian Gulf", "Mediterranean"): ("hormuz", "bab_el_mandeb", "suez"),
    ("Persian Gulf", "North America East Coast"): ("hormuz", "bab_el_mandeb", "suez", "gibraltar"),
    ("Middle East", "East Asia"): ("hormuz", "malacca"),
    ("Middle East", "Southeast Asia"): ("hormuz", "malacca"),
    ("Middle East", "Europe"): ("hormuz", "bab_el_mandeb", "suez"),
    ("Europe", "East Asia"): ("suez", "bab_el_mandeb", "malacca"),
    ("Europe", "Southeast Asia"): ("suez", "bab_el_mandeb", "malacca"),
    ("Europe", "North America East Coast"): ("gibraltar",),
    ("Europe", "North America West Coast"): ("gibraltar", "panama"),
    ("East Asia", "North America West Coast"): (),
    ("East Asia", "North America East Coast"): ("panama",),
    ("Southeast Asia", "Europe"): ("malacca", "bab_el_mandeb", "suez"),
}


def valid_destinations(start: str) -> list[str]:
    """Return a list of regions that have a defined route from the start region."""
    valid = set()
    for (s, e) in ROUTE_RULES:
        if s == start:
            valid.add(e)
        elif e == start:
            valid.add(s)
    return sorted(list(valid))


def route_for(start: str, end: str) -> list[Chokepoint]:
>>>>>>> 5846824e413d4d903386ab94377a94904781a7aa
    """Return ordered chokepoints for a supported illustrative route.

    Returns ``None`` when the origin-destination pair has no rule at all —
    an unsupported pair; the caller should say so plainly and stop.

    Returns an empty list when the pair *is* covered but the modeled
    corridor legitimately has no major chokepoint (a documented open-ocean
    route, e.g. trans-Pacific). The caller must not treat this the same as
    "unsupported" — it is a correct answer, not a missing one.
    """
    if start == end:
        return None
    pair = (start, end)
<<<<<<< HEAD
    if pair in _ROUTE_RULES:
        return [CHOKEPOINTS[key] for key in _ROUTE_RULES[pair]]
    reversed_pair = (end, start)
    if reversed_pair in _ROUTE_RULES:
        return [CHOKEPOINTS[key] for key in reversed(_ROUTE_RULES[reversed_pair])]
    return None


def alternative_origins(end: str, exclude: str) -> list[str]:
    """Regions other than `exclude` with a known modeled route to `end`.

    Used by the Adaptive Procurement Orchestrator to find alternative
    sourcing origins worth comparing against the currently selected start
    region. Only pairs already present in the fixed rules table are
    considered -- this never invents a route for an unsupported pair, and a
    region whose only relationship to `end` is a documented open-ocean
    (chokepoint-free) corridor is included too, since that is still a valid,
    scoreable route in this model.
    """
    return [region for region in REGIONS if region not in (end, exclude) and route_for(region, end) is not None]
=======
    if pair in ROUTE_RULES:
        return [CHOKEPOINTS[key] for key in ROUTE_RULES[pair]]
    reversed_pair = (end, start)
    if reversed_pair in ROUTE_RULES:
        return [CHOKEPOINTS[key] for key in reversed(ROUTE_RULES[reversed_pair])]
    return []
>>>>>>> 5846824e413d4d903386ab94377a94904781a7aa
