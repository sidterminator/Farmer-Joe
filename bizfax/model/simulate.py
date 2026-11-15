"""Monte Carlo arrival-date simulation over a carrier's route legs.

Each leg: wait for a working day -> base lognormal duration -> weather delay draw.
US customs (assumed distribution) is inserted after the leg flagged customs_after.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from bizfax.config import CUSTOMS_MEDIAN_HOURS, CUSTOMS_SIGMA, N_SIMULATIONS, PICKUP_HOUR, Carrier
from bizfax.data.calendar import is_holiday

HORIZON_DAYS = 30


def _working_mask(leg, start: dt.date) -> np.ndarray:
    days = [start + dt.timedelta(days=i) for i in range(HORIZON_DAYS)]
    return np.array([
        d.weekday() in leg.works_on and not (leg.holiday_country and is_holiday(leg.holiday_country, d))
        for d in days
    ])


def _wait_for_working_day(t: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """t in hours since ship-date midnight. Push to 08:00 of next working day if needed."""
    t = t.copy()
    for _ in range(HORIZON_DAYS):
        day = np.minimum((t // 24).astype(int), HORIZON_DAYS - 1)
        closed = ~mask[day]
        if not closed.any():
            break
        t[closed] = (day[closed] + 1) * 24 + 8
    return t


def simulate_carrier(
    carrier: Carrier,
    ship_date: dt.date,
    p_delay_by_node: dict[str, pd.Series],
    n: int = N_SIMULATIONS,
    seed: int = 0,
) -> np.ndarray:
    """Return n simulated arrival times in hours since ship-date midnight.

    p_delay_by_node: airport code -> Series indexed by date with daily delay probability.
    Missing dates/nodes default to 0.
    """
    rng = np.random.default_rng(seed)
    t = np.full(n, float(PICKUP_HOUR))
    for leg in carrier.legs:
        t = _wait_for_working_day(t, _working_mask(leg, ship_date))
        t = t + rng.lognormal(np.log(leg.median_hours), leg.sigma, n)
        if leg.weather_node:
            series = p_delay_by_node.get(leg.weather_node, pd.Series(dtype=float))
            days = [ship_date + dt.timedelta(days=i) for i in range(HORIZON_DAYS)]
            p = np.array([float(series.get(d, 0.0)) for d in days])
            day = np.minimum((t // 24).astype(int), HORIZON_DAYS - 1)
            hit = rng.random(n) < p[day]
            t = t + hit * rng.exponential(leg.delay_mean_hours, n)
        if leg.customs_after:
            t = t + rng.lognormal(np.log(CUSTOMS_MEDIAN_HOURS), CUSTOMS_SIGMA, n)
    return t


def arrival_dates(hours: np.ndarray, ship_date: dt.date) -> np.ndarray:
    days = (hours // 24).astype(int)
    return np.array([ship_date + dt.timedelta(days=int(d)) for d in days])


def summarize(hours: np.ndarray, ship_date: dt.date, deadline: dt.date | None = None) -> dict:
    """Percentile arrival dates (P10/P50/P90) and P(on or before deadline)."""
    day_offsets = hours // 24
    pct = {q: ship_date + dt.timedelta(days=int(np.percentile(day_offsets, q))) for q in (10, 50, 90)}
    out = {"p10": pct[10], "p50": pct[50], "p90": pct[90]}
    if deadline is not None:
        out["p_on_time"] = float(np.mean(day_offsets <= (deadline - ship_date).days))
    return out
