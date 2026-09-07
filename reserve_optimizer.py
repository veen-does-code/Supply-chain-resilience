"""Transparent strategic-reserve drawdown simulation for the dashboard."""

from __future__ import annotations

import pandas as pd


def optimise_reserve_drawdown(
    projected_risk: float,
    reserve_days: int,
    safety_floor_days: int,
    horizon_days: int,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Create a conservative daily reserve schedule from a risk stress test.

    The supply-gap profile is illustrative: risk above the project's medium
    threshold (25) translates to a gradually increasing percentage of daily
    demand that must be covered. The scheduler never draws below the chosen
    strategic safety floor.
    """
    usable_reserve = max(0.0, float(reserve_days - safety_floor_days))
    maximum_gap = min(0.45, max(0.0, (projected_risk - 25.0) / 170.0))
    rows: list[dict[str, float | int]] = []
    remaining = usable_reserve

    for day in range(1, horizon_days + 1):
        # A modest escalation allows planning teams to protect early reserves
        # while still modelling the possibility of a persistent disruption.
        escalation = 0.65 + 0.35 * ((day - 1) / max(1, horizon_days - 1))
        forecast_gap = maximum_gap * escalation
        drawdown = min(forecast_gap, remaining)
        remaining -= drawdown
        rows.append({
            "Day": day,
            "Forecast supply gap (% of daily demand)": forecast_gap * 100,
            "Recommended reserve drawdown (days)": drawdown,
            "Reserve remaining (days)": safety_floor_days + remaining,
        })

    schedule = pd.DataFrame(rows)
    total_drawdown = float(schedule["Recommended reserve drawdown (days)"].sum())
    uncovered_gap = float((schedule["Forecast supply gap (% of daily demand)"] / 100).sum() - total_drawdown)
    return schedule, {
        "total_drawdown": total_drawdown,
        "reserve_remaining": safety_floor_days + remaining,
        "uncovered_gap": max(0.0, uncovered_gap),
        "peak_gap_percent": maximum_gap * 100,
    }
