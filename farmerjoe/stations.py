"""Market stations: GHCN ID lookup, verification, nearest-K selection (CLAUDE.md 6.6)."""
from __future__ import annotations

import json
import re
import warnings
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

EARTH_KM = 6371.0088
NCEI_URL = "https://www.ncei.noaa.gov/access/services/data/v1"
REQUIRED_ELEMENTS = ("TMAX", "TMIN", "PRCP")
MATCH_RADIUS_KM = 15.0
MIN_OVERLAP_YEARS = 10


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km (vectorized)."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi, dlmb = p2 - p1, np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return 2 * EARTH_KM * np.arcsin(np.sqrt(a))


@dataclass
class Station:
    code: str
    ghcn_id: str
    name: str
    lat: float
    lon: float
    markets: list[str]
    verified_market: bool
    first_year: int
    last_year: int
    distance_km: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def as_meta(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("extra")
        d.update(self.extra)
        return d


def find_ghcn_candidates(lat: float, lon: float, stations: pd.DataFrame, inventory: pd.DataFrame,
                         years: tuple[int, int], radius_km: float = MATCH_RADIUS_KM) -> pd.DataFrame:
    """GHCN stations within radius that report TMAX/TMIN/PRCP, sorted best first:
    USW (first-order) before others, then longest common record overlapping `years`, then distance."""
    st = stations.assign(dist_km=haversine_km(lat, lon, stations["lat"].to_numpy(), stations["lon"].to_numpy()))
    st = st[st["dist_km"] <= radius_km]
    if st.empty:
        return st
    inv = inventory[inventory["id"].isin(st["id"]) & inventory["element"].isin(REQUIRED_ELEMENTS)]
    cov = inv.groupby("id").agg(n_el=("element", "nunique"), first_year=("first_year", "max"),
                                last_year=("last_year", "min"))
    st = st.merge(cov, left_on="id", right_index=True)
    st = st[st["n_el"] == len(REQUIRED_ELEMENTS)]
    overlap = (np.minimum(st["last_year"], years[1]) - np.maximum(st["first_year"], years[0]) + 1).clip(lower=0)
    st = st.assign(usw=st["id"].str.startswith("USW"), overlap=overlap)
    st = st[st["overlap"] >= MIN_OVERLAP_YEARS]   # a closed station can't stand in for a live market
    return st.sort_values(["usw", "overlap", "dist_km"], ascending=[False, False, True])


def _verify_with_ncei(ghcn_id: str, lat: float, lon: float) -> dict[str, Any]:
    """Ask the NCEI data service for the station's name/coords (one recent day)."""
    params = {"dataset": "daily-summaries", "stations": ghcn_id, "startDate": "2024-07-01",
              "endDate": "2024-07-07", "dataTypes": "TMAX", "format": "json",
              "includeStationName": "true", "includeStationLocation": "1"}
    resp = requests.get(NCEI_URL, params=params, timeout=120)
    resp.raise_for_status()
    rows = resp.json()
    if not rows:
        raise RuntimeError(f"NCEI returned no data for {ghcn_id}")
    r = rows[0]
    d = float(haversine_km(lat, lon, float(r["LATITUDE"]), float(r["LONGITUDE"])))
    return {"ncei_name": r.get("NAME", ""), "ncei_lat": float(r["LATITUDE"]),
            "ncei_lon": float(r["LONGITUDE"]), "ncei_offset_km": round(d, 2)}


def resolve_market_stations(market: dict[str, dict[str, Any]], stations: pd.DataFrame,
                            inventory: pd.DataFrame, years: tuple[int, int],
                            cache_path: str | Path, verify: bool = True,
                            codes: list[str] | None = None) -> dict[str, Station]:
    """Resolve market-station codes to verified GHCN stations (cached in cache_path JSON)."""
    cache_path = Path(cache_path)
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    out: dict[str, Station] = {}
    for code in codes or list(market):
        m = market[code]
        key = f"{code}:{m['lat']:.3f},{m['lon']:.3f}"
        if key not in cache:
            cands = find_ghcn_candidates(m["lat"], m["lon"], stations, inventory, years)
            if cands.empty:
                raise RuntimeError(f"{code}: no GHCN station with TMAX/TMIN/PRCP and >= {MIN_OVERLAP_YEARS} "
                                   f"years of history within {MATCH_RADIUS_KM} km")
            hint = str(m.get("name_hint", "")).upper()
            if hint:  # name match only breaks ties between equally covered candidates
                cands = cands.assign(hint=cands["name"].str.upper().str.contains(hint, regex=False))
                cands = cands.sort_values(["usw", "overlap", "hint", "dist_km"], ascending=[False, False, False, True])
            best = cands.iloc[0]
            entry = {"ghcn_id": best["id"], "name": best["name"], "lat": float(best["lat"]),
                     "lon": float(best["lon"]), "first_year": int(best["first_year"]),
                     "last_year": int(best["last_year"]), "match_km": round(float(best["dist_km"]), 2)}
            if verify:
                v = _verify_with_ncei(entry["ghcn_id"], entry["lat"], entry["lon"])
                if v["ncei_offset_km"] > 2.0:
                    raise RuntimeError(f"{code}: NCEI coords differ from metadata by {v['ncei_offset_km']} km")
                entry.update(v, verified_ghcn=True)
            cache[key] = entry
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(cache, indent=2))
        e = cache[key]
        out[code] = Station(code=code, ghcn_id=e["ghcn_id"], name=e.get("ncei_name") or e["name"],
                            lat=e["lat"], lon=e["lon"], markets=list(m.get("markets", [])),
                            verified_market=bool(m.get("verified_market", False)),
                            first_year=e["first_year"], last_year=e["last_year"])
    return out


def select_stations(lat: float, lon: float, market: dict[str, dict[str, Any]], k: int,
                    explicit: list[str] | None = None, max_km: float = 400.0) -> list[str]:
    """Codes of the K nearest market stations with at least one market (or the explicit list)."""
    if explicit:
        return list(explicit)
    rows = [(c, float(haversine_km(lat, lon, m["lat"], m["lon"]))) for c, m in market.items() if m.get("markets")]
    rows.sort(key=lambda r: r[1])
    chosen = rows[:k]
    if chosen and chosen[0][1] > max_km:
        warnings.warn(f"nearest market station {chosen[0][0]} is {chosen[0][1]:.0f} km from the farm "
                      f"(> {max_km:.0f} km): expect large basis risk", stacklevel=2)
    return [c for c, _ in chosen]


_ENTRY = re.compile(r"\{([^{}]*\bid:\s*'[a-z]+'[^{}]*)\}")
_PAIR = re.compile(r"(\w+):\s*('(?:[^'\\]|\\.)*'|-?\d+(?:\.\d+)?)")


def markets_from_series(series: str) -> list[str]:
    """Which market types a Kalshi series ticker covers (rain / daily high / daily low)."""
    s = series.upper()
    if "RAIN" in s:
        return ["rain"]
    if "HIGH" in s:
        return ["tmax"]
    if "LOW" in s:
        return ["tmin"]
    return []


def load_market_stations_js(path: str | Path) -> dict[str, dict[str, Any]]:
    """Parse the frontend's station list (frontend/stations.js, the single source of truth)
    into {CODE: {lat, lon, city, series, markets, verified_market}}. Coordinates there are
    approximate (airport, 2 decimals); the GHCN lookup snaps them to the real station."""
    text = Path(path).read_text()
    out: dict[str, dict[str, Any]] = {}
    for m in _ENTRY.finditer(text):
        kv = {}
        for k, v in _PAIR.findall(m.group(1)):
            kv[k] = v[1:-1].replace("\\'", "'") if v.startswith("'") else float(v)
        code = str(kv["id"]).upper()
        out[code] = {"lat": float(kv["lat"]), "lon": float(kv["lon"]), "city": kv.get("city", code),
                     "name_hint": "", "series": kv.get("series", ""),
                     "markets": markets_from_series(str(kv.get("series", ""))),
                     # The series ticker is real (read from Kalshi); which airport it settles
                     # on is not yet confirmed, so markets stay unverified.
                     "verified_market": False}
    if not out:
        raise ValueError(f"no stations parsed from {path}")
    return out
