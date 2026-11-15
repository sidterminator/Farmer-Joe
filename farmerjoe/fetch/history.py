"""Daily observation history.

Stations: NOAA NCEI Access Data Service, dataset `daily-summaries` (GHCN-Daily).
Daily values are NWS climatological days, which run midnight-to-midnight LOCAL STANDARD
TIME (so 1am-1am CDT in summer). We keep NCEI's date as the local date; no re-aggregation.

Every chunk is cached to data/raw/ as parquet and read from the cache on later calls.
"""
from __future__ import annotations

import datetime as dt
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

NCEI_URL = "https://www.ncei.noaa.gov/access/services/data/v1"
OBS_COLUMNS = ["date", "tmax_f", "tmin_f", "precip_in"]
_NCEI_VARS = {"TMAX": "tmax_f", "TMIN": "tmin_f", "PRCP": "precip_in"}
CHUNK_YEARS = 5


def parse_ncei_records(records: list[dict]) -> pd.DataFrame:
    """Parse NCEI JSON rows (units=standard, includeAttributes=true) into OBS_COLUMNS.

    - Missing values (key absent or blank) become NaN.
    - Values with a non-blank GHCN quality flag (2nd attribute field) become NaN.
    - Trace precipitation (measurement flag 'T') is reported as 0.00 -> stays 0 (dry day).
    """
    rows = []
    for r in records:
        row = {"date": dt.date.fromisoformat(r["DATE"][:10])}
        for src, dst in _NCEI_VARS.items():
            val = pd.to_numeric(str(r.get(src, "")).strip() or np.nan, errors="coerce")
            attrs = str(r.get(f"{src}_ATTRIBUTES", "")).split(",")
            qflag = attrs[1].strip() if len(attrs) > 1 else ""
            row[dst] = np.nan if qflag else float(val)
        rows.append(row)
    df = pd.DataFrame(rows, columns=OBS_COLUMNS)
    return df.sort_values("date").drop_duplicates("date").reset_index(drop=True)


def _get_json(params: dict, retries: int = 4, timeout: int = 120) -> list[dict]:
    for attempt in range(retries):
        try:
            resp = requests.get(NCEI_URL, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError):
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt * 3)
    return []


def fetch_station_history(station_id: str, start: dt.date, end: dt.date,
                          cache_dir: str | Path = "data/raw") -> pd.DataFrame:
    """Daily TMAX/TMIN/PRCP for a GHCN station, in °F / inches, one row per calendar day
    in [start, end] (missing days present as NaN rows). Fetched in 5-year chunks."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    parts = []
    y = start.year
    while y <= end.year:
        c0 = max(start, dt.date(y, 1, 1))
        c1 = min(end, dt.date(y + CHUNK_YEARS - 1, 12, 31))
        path = cache_dir / f"ghcn_{station_id}_{c0:%Y%m%d}_{c1:%Y%m%d}.parquet"
        if path.exists():
            part = pd.read_parquet(path)
        else:
            recs = _get_json({
                "dataset": "daily-summaries", "stations": station_id,
                "startDate": c0.isoformat(), "endDate": c1.isoformat(),
                "dataTypes": "TMAX,TMIN,PRCP", "units": "standard", "format": "json",
                "includeAttributes": "true",
            })
            part = parse_ncei_records(recs)
            part.to_parquet(path, index=False)
        parts.append(part)
        y += CHUNK_YEARS
    df = pd.concat(parts, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    full = pd.DataFrame({"date": pd.date_range(start, end, freq="D").date})
    return full.merge(df, on="date", how="left")[OBS_COLUMNS]


# ------------------------------------------------------------------ Open-Meteo (farm + index)
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"


class CallBudget:
    """Client-side throttle for Open-Meteo's free tier (600 calls/min, 5,000/h, 10,000/day).

    Open-Meteo counts a request spanning more than 2 weeks as several calls (their example:
    4 weeks = 3 calls), so we estimate weight = 1.5 * max(1, days / 14) and keep a rolling
    60 s window under `per_min`.
    """

    def __init__(self, per_min: float = 450.0):
        self.per_min = per_min
        self.events: list[tuple[float, float]] = []
        self.total = 0.0

    @staticmethod
    def weight(days: int) -> float:
        return 1.5 * max(1.0, days / 14.0)

    def spend(self, w: float) -> None:
        while True:
            now = time.monotonic()
            self.events = [(t, x) for t, x in self.events if now - t < 60.0]
            if sum(x for _, x in self.events) + w <= self.per_min:
                break
            time.sleep(1.0)
        self.events.append((time.monotonic(), w))
        self.total += w


DEFAULT_BUDGET = CallBudget()


def _openmeteo_get(params: dict, budget: CallBudget, days: int, retries: int = 6) -> dict:
    for attempt in range(retries):
        budget.spend(budget.weight(days))
        try:
            resp = requests.get(OPEN_METEO_URL, params=params, timeout=(20, 90))
        except (requests.Timeout, requests.ConnectionError):
            time.sleep(10 * (attempt + 1))    # transient network trouble: retry
            continue
        if resp.status_code == 429:           # over the limit: back off hard
            time.sleep(60 * (attempt + 1))
            continue
        if resp.status_code >= 500:
            time.sleep(10 * (attempt + 1))
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError("Open-Meteo: retries exhausted (rate limit or network)")


def fetch_openmeteo_season(lat: float, lon: float, years: tuple[int, int], months: tuple[int, int],
                           cache_dir: str | Path = "data/raw", budget: CallBudget | None = None) -> pd.DataFrame:
    """Daily tmax/tmin/precip at a grid point for months [m0, m1] of each year in `years`.

    One request per year (keeps each request short, see CallBudget). Gridded reanalysis,
    local dates via timezone=auto. Cached per point+months; resumes missing years.
    df.attrs["timezone"] holds the IANA zone.
    """
    import calendar as _cal

    budget = budget or DEFAULT_BUDGET
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"openmeteo_{lat:.3f}_{lon:.3f}_m{months[0]:02d}-{months[1]:02d}.parquet"
    have = pd.read_parquet(path) if path.exists() else pd.DataFrame(columns=OBS_COLUMNS + ["timezone"])
    have_years = set(pd.to_datetime(have["date"]).dt.year) if len(have) else set()
    parts = [have]
    for y in range(years[0], years[1] + 1):
        if y in have_years:
            continue
        s = dt.date(y, months[0], 1)
        e = dt.date(y, months[1], _cal.monthrange(y, months[1])[1])
        js = _openmeteo_get({
            "latitude": lat, "longitude": lon, "start_date": s.isoformat(), "end_date": e.isoformat(),
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "temperature_unit": "fahrenheit", "precipitation_unit": "inch", "timezone": "auto",
        }, budget, (e - s).days + 1)
        d = js["daily"]
        parts.append(pd.DataFrame({
            "date": pd.to_datetime(d["time"]).date, "tmax_f": d["temperature_2m_max"],
            "tmin_f": d["temperature_2m_min"], "precip_in": d["precipitation_sum"],
            "timezone": js.get("timezone", ""),
        }))
        # save as we go so an interrupted fetch resumes
        pd.concat(parts, ignore_index=True).to_parquet(path, index=False)
    df = pd.concat(parts, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    for c in ("tmax_f", "tmin_f", "precip_in"):
        df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
    df = df.sort_values("date").drop_duplicates("date")
    yrs = pd.to_datetime(df["date"]).dt.year
    df = df[yrs.between(*years)]
    out = df[OBS_COLUMNS].reset_index(drop=True)
    out.attrs["timezone"] = str(df["timezone"].iloc[0]) if len(df) else ""
    return out


def fetch_index_history(points: list[list[float]], years: tuple[int, int], months: tuple[int, int],
                        cache_dir: str | Path = "data/raw", budget: CallBudget | None = None) -> pd.DataFrame:
    """Production-region index: daily mean of tmax, tmin, precip over the region's points.
    (Season variables are then computed from this averaged series.)"""
    frames = [fetch_openmeteo_season(p[0], p[1], years, months, cache_dir, budget).set_index("date")
              for p in points]
    stacked = pd.concat(frames, keys=range(len(frames)))
    mean = stacked.groupby(level="date").mean()
    n = stacked.groupby(level="date").size()
    mean[n < len(points)] = np.nan   # a day missing at any point -> missing for the index
    return mean.reset_index()[OBS_COLUMNS]
