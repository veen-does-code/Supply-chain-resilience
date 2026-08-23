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
    """Return ordered chokepoints for a supported illustrative route.

    The rules cover energy-shipping corridors, not every global pair.  Reversing
    a known corridor reverses its chokepoint order.
    """
    if start == end:
        return []
    pair = (start, end)
    if pair in ROUTE_RULES:
        return [CHOKEPOINTS[key] for key in ROUTE_RULES[pair]]
    reversed_pair = (end, start)
    if reversed_pair in ROUTE_RULES:
        return [CHOKEPOINTS[key] for key in reversed(ROUTE_RULES[reversed_pair])]
    return []
