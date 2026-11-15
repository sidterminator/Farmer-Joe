"""Daily scenarios -> season totals (CLAUDE.md section 6.1)."""
from __future__ import annotations

import numpy as np
import pandas as pd

HOT_DAY_F = 95.0
GDD_BASE_F = 50.0
GDD_CAP_F = 86.0


def gdd_daily(tmax: np.ndarray, tmin: np.ndarray) -> np.ndarray:
    """Corn GDD per day: max(0, (min(tmax, 86) + max(tmin, 50)) / 2 - 50)."""
    tmax_c = np.minimum(tmax, GDD_CAP_F)
    tmin_c = np.maximum(tmin, GDD_BASE_F)
    return np.maximum(0.0, (tmax_c + tmin_c) / 2.0 - GDD_BASE_F)


def daily_to_arrays(daily: pd.DataFrame, locations: list[str]) -> dict[str, np.ndarray]:
    """Pivot long daily table to arrays of shape (N, D, L) per variable, sorted by
    scenario_id and date, with the location axis in `locations` order."""
    d = daily.sort_values(["scenario_id", "date"])
    n = d["scenario_id"].nunique()
    n_days = d["date"].nunique()
    out = {}
    for var in ("tmax_f", "tmin_f", "precip_in"):
        stacks = []
        for loc in locations:
            sub = d.loc[d["location"] == loc, var].to_numpy(dtype=np.float64)
            stacks.append(sub.reshape(n, n_days))
        out[var] = np.stack(stacks, axis=-1)
    return out


def season_totals(tmax: np.ndarray, tmin: np.ndarray, precip: np.ndarray,
                  locations: list[str]) -> pd.DataFrame:
    """Season variables from (N, D, L) arrays -> wide scenarios_season frame."""
    n = tmax.shape[0]
    rain = precip.sum(axis=1)
    hot = (tmax >= HOT_DAY_F).sum(axis=1)
    gdd = gdd_daily(tmax, tmin).sum(axis=1)
    cols: dict[str, np.ndarray] = {"scenario_id": np.arange(n, dtype=np.int32)}
    for j, loc in enumerate(locations):
        cols[f"rain_total_in_{loc}"] = rain[:, j].astype(np.float32)
        cols[f"hot_days_95_{loc}"] = hot[:, j].astype(np.int32)
        cols[f"gdd_{loc}"] = gdd[:, j].astype(np.float32)
    return pd.DataFrame(cols)


def daily_to_season(daily: pd.DataFrame, locations: list[str]) -> pd.DataFrame:
    """Convenience wrapper: long daily table -> wide season table."""
    a = daily_to_arrays(daily, locations)
    return season_totals(a["tmax_f"], a["tmin_f"], a["precip_in"], locations)


def basis_risk(season: pd.DataFrame, stations: list[str]) -> dict[str, dict[str, float]]:
    """Pearson correlation of farm vs each station for season rain and hot days."""
    out: dict[str, dict[str, float]] = {}
    for var in ("rain_total_in", "hot_days_95", "gdd"):
        farm = season[f"{var}_farm"].to_numpy(dtype=float)
        out[var] = {}
        for st in stations:
            x = season[f"{var}_{st}"].to_numpy(dtype=float)
            ok = farm.std() > 0 and x.std() > 0
            out[var][st] = round(float(np.corrcoef(farm, x)[0, 1]), 4) if ok else None
    return out
