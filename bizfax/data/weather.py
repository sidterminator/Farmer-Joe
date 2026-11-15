"""Open-Meteo weather: forecast for the near term, climatology beyond it.

Returns one DataFrame per airport indexed by date with WEATHER_VARS columns.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import requests

from bizfax.config import CLIMATOLOGY_YEARS, FORECAST_TRUST_DAYS, PLACES, WEATHER_VARS

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def _daily(url: str, lat: float, lon: float, **params) -> pd.DataFrame:
    resp = requests.get(url, params={
        "latitude": lat, "longitude": lon, "daily": ",".join(WEATHER_VARS),
        "timezone": "UTC", **params,
    }, timeout=30)
    resp.raise_for_status()
    daily = resp.json()["daily"]
    df = pd.DataFrame(daily)
    df["time"] = pd.to_datetime(df["time"]).dt.date
    return df.set_index("time")


def historical(code: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    """Observed daily weather (ERA5-based archive). Use for backtests and replays."""
    _, lat, lon = PLACES[code]
    return _daily(ARCHIVE_URL, lat, lon, start_date=start.isoformat(), end_date=end.isoformat())


def forecast(code: str, days: int = 16) -> pd.DataFrame:
    _, lat, lon = PLACES[code]
    return _daily(FORECAST_URL, lat, lon, forecast_days=days)


def climatology(code: str, start: dt.date, end: dt.date, years: int = CLIMATOLOGY_YEARS) -> pd.DataFrame:
    """Mean of the same calendar dates over the previous `years` years."""
    frames = []
    for y in range(1, years + 1):
        s, e = start.replace(year=start.year - y), end.replace(year=end.year - y)
        df = historical(code, s, e)
        df.index = [d.replace(year=d.year + y) for d in df.index]
        frames.append(df)
    return pd.concat(frames).groupby(level=0).mean()


def weather_for_window(code: str, start: dt.date, end: dt.date, today: dt.date | None = None) -> pd.DataFrame:
    """Forecast for days within FORECAST_TRUST_DAYS of today, climatology after.

    For historical replays (end < today - 5 days), returns observed weather instead,
    i.e. a "perfect forecast" replay. Column `source` says which was used.
    """
    today = today or dt.date.today()
    if end < today - dt.timedelta(days=5):
        df = historical(code, start, end)
        df["source"] = "observed"
        return df
    idx = pd.Index([start + dt.timedelta(days=i) for i in range((end - start).days + 1)])
    trust_until = today + dt.timedelta(days=FORECAST_TRUST_DAYS)
    fc = forecast(code)
    fc["source"] = "forecast"
    clim = climatology(code, start, end)
    clim["source"] = "climatology"
    out = clim.reindex(idx)
    near = [d for d in idx if d <= trust_until and d in fc.index]
    out.loc[near] = fc.loc[near]
    return out
