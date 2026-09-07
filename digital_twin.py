"""Interactive, illustrative geospatial digital twin for modeled sea routes.

The app deliberately models only the listed regional hubs and chokepoints. It
is a decision-support simulation, not AIS vessel tracking or route planning.
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd
import pydeck as pdk

from routes import Chokepoint


# Representative offshore/port locations for the high-level regions used by
# routes.py. These anchors make the fixed route heuristic visible on a map.
REGION_COORDINATES: dict[str, tuple[float, float]] = {
    "Persian Gulf": (25.27, 55.30),
    "Middle East": (24.71, 46.68),
    "South Asia": (19.08, 72.88),
    "Southeast Asia": (1.29, 103.85),
    "East Asia": (31.23, 121.47),
    "Europe": (51.92, 4.48),
    "Mediterranean": (31.20, 29.92),
    "North America East Coast": (40.68, -74.04),
    "North America West Coast": (33.74, -118.27),
    "West Africa": (6.45, 3.39),
}


def _node_color(risk: float | None, affected: bool) -> list[int]:
    if affected:
        return [239, 68, 68]
    if risk is None:
        return [148, 163, 184]
    if risk >= 50:
        return [239, 68, 68]
    if risk >= 25:
        return [245, 158, 11]
    return [34, 197, 94]


def create_twin_deck(
    start: str,
    end: str,
    route: Iterable[Chokepoint],
    node_risks: dict[str, float],
    affected_key: str | None = None,
) -> pdk.Deck:
    """Render route anchors, chokepoint nodes, and the modeled corridor."""
    route = list(route)
    start_lat, start_lon = REGION_COORDINATES[start]
    end_lat, end_lon = REGION_COORDINATES[end]
    points = [
        {"name": start, "kind": "Origin", "latitude": start_lat, "longitude": start_lon,
         "risk": None, "color": [59, 130, 246]},
        *[
            {
                "name": checkpoint.name,
                "kind": "Chokepoint",
                "latitude": checkpoint.latitude,
                "longitude": checkpoint.longitude,
                "risk": node_risks.get(checkpoint.key),
                "color": _node_color(node_risks.get(checkpoint.key), checkpoint.key == affected_key),
            }
            for checkpoint in route
        ],
        {"name": end, "kind": "Destination", "latitude": end_lat, "longitude": end_lon,
         "risk": None, "color": [139, 92, 246]},
    ]
    path = [[point["longitude"], point["latitude"]] for point in points]
    midpoint = points[len(points) // 2]
    path_frame = pd.DataFrame([{"path": path}])
    point_frame = pd.DataFrame(points)
    return pdk.Deck(
        # Streamlit supplies this named basemap without requiring users to
        # configure a personal Mapbox token for the hackathon demo.
        map_style="dark",
        initial_view_state=pdk.ViewState(latitude=midpoint["latitude"], longitude=midpoint["longitude"], zoom=2.1, pitch=20),
        layers=[
            pdk.Layer("PathLayer", data=path_frame, get_path="path", get_color=[56, 189, 248], get_width=4, width_min_pixels=3),
            pdk.Layer(
                "ScatterplotLayer", data=point_frame, get_position="[longitude, latitude]",
                get_fill_color="color", get_radius=85000, radius_min_pixels=7,
                pickable=True,
            ),
        ],
        tooltip={"html": "<b>{name}</b><br/>{kind}<br/>Current risk: {risk}", "style": {"backgroundColor": "#0f172a", "color": "white"}},
    )


def run_scenario(base_score: float, node_risks: dict[str, float], affected_key: str | None, severity: int) -> dict[str, float]:
    """Calculate transparent, bounded what-if outputs for a selected shock."""
    current_node_risk = node_risks.get(affected_key or "", 0.0)
    exposure = (current_node_risk / 100) if current_node_risk else 0.5
    shock_points = severity * (0.35 + 0.65 * exposure)
    projected_risk = min(100.0, base_score + shock_points)
    return {
        "projected_risk": projected_risk,
        "risk_change": projected_risk - base_score,
        "reliability": max(0.0, 100 - projected_risk),
        "estimated_delay_days": round((severity / 100) * (2.0 + 8.0 * exposure), 1),
    }
