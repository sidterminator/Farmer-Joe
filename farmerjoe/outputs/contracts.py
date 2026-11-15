"""Candidate contracts, payoff matrix, and model probabilities (CLAUDE.md section 7).

Teammates' optimizer imports `payoff_matrix`.

Comparator semantics (x = contract variable, t = threshold, hi = threshold_hi):
    lt: x < t    le: x <= t    gt: x > t    ge: x >= t    between: t <= x <= hi (inclusive)
Season-type variables (rain_total_in, hot_days_95, gdd) covering the full simulated window are
read from the season table; shorter periods (e.g., one calendar month of a two-month window)
are computed from the daily table. Daily variables (tmax_f, tmin_f, precip_in) must be
single-day contracts (start == end).
"""
from __future__ import annotations

import calendar as _cal
import datetime as dt

import numpy as np
import pandas as pd

from farmerjoe.outputs.schema import CONTRACT_COLUMNS, DAILY_VARS, SEASON_VARS

_VAR_TAG = {"rain_total_in": "RAIN", "hot_days_95": "HOT95", "gdd": "GDD",
            "tmax_f": "TMAX", "tmin_f": "TMIN", "precip_in": "PRCP"}


def _period_tag(start: dt.date, end: dt.date) -> str:
    if start == end:
        return start.strftime("%Y%m%d")
    if (start.year, start.month) == (end.year, end.month):
        return start.strftime("%b").upper()
    return f"{start:%Y%m%d}-{end:%Y%m%d}"


def _fmt(t: float) -> str:
    return f"{t:.1f}" if float(t) != int(t) or t < 10 else f"{int(t)}"


def contract_id(location: str, variable: str, comparator: str, threshold: float,
                start: dt.date, end: dt.date, threshold_hi: float | None = None) -> str:
    """Build our id, e.g. ORD_RAIN_JUL_LT_2.5 or ORD_TMAX_20270701_GE_95."""
    thr = _fmt(threshold) if threshold_hi is None else f"{_fmt(threshold)}-{_fmt(threshold_hi)}"
    return f"{location}_{_VAR_TAG[variable]}_{_period_tag(start, end)}_{comparator.upper()}_{thr}"


def calendar_months(start: dt.date, end: dt.date) -> list[tuple[dt.date, dt.date]]:
    """Whole calendar months inside [start, end] as (first day, last day)."""
    out, y, m = [], start.year, start.month
    while dt.date(y, m, 1) <= end:
        a = dt.date(y, m, 1)
        b = dt.date(y, m, _cal.monthrange(y, m)[1])
        if a >= start and b <= end:
            out.append((a, b))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def candidate_contracts(stations: list[str] | dict[str, list[str]], start: dt.date, end: dt.date,
                        forecast_days: list[dt.date], grid: dict) -> pd.DataFrame:
    """Default candidate grid, per station and only for the markets it has (`stations` may be
    {code: markets}; a plain list means every station has rain and tmax markets):
    rain-total thresholds (lt and ge) for each calendar month in the window, plus daily tmax
    thresholds for each forecast-window day. p columns left NaN."""
    if not isinstance(stations, dict):
        stations = {s: ["rain", "tmax"] for s in stations}
    months = calendar_months(start, end) or [(start, end)]
    rg = grid.get("rain_total_thresholds", {"start": 1.0, "stop": 7.0, "step": 0.5})
    rain_thr = np.round(np.arange(rg["start"], rg["stop"] + rg["step"] / 2, rg["step"]), 4)
    rain_cmps = grid.get("rain_total_comparators", ["lt", "ge"])
    tmax_thr = grid.get("daily_tmax_thresholds", [85, 90, 95, 100])
    tmax_cmp = grid.get("daily_tmax_comparator", "ge")

    rows = []
    for st, markets in stations.items():
        if "rain" in markets:
            for m0, m1 in months:
                for cmp in rain_cmps:
                    for t in rain_thr:
                        rows.append(dict(location=st, variable="rain_total_in", comparator=cmp,
                                         threshold=float(t), start=m0, end=m1))
        if "tmax" not in markets:
            continue
        for day in forecast_days:
            for t in tmax_thr:
                rows.append(dict(location=st, variable="tmax_f", comparator=tmax_cmp,
                                 threshold=float(t), start=day, end=day))
    df = pd.DataFrame(rows)
    df["threshold_hi"] = np.nan
    df["contract_id"] = [contract_id(r.location, r.variable, r.comparator, r.threshold, r.start, r.end)
                         for r in df.itertuples()]
    df["ticker"] = ""
    df["p_model"] = np.nan
    df["p_se"] = np.nan
    return df[CONTRACT_COLUMNS]


def _compare(x: np.ndarray, comparator: str, t: float, hi: float | None) -> np.ndarray:
    if comparator == "lt":
        return x < t
    if comparator == "le":
        return x <= t
    if comparator == "gt":
        return x > t
    if comparator == "ge":
        return x >= t
    if comparator == "between":
        return (x >= t) & (x <= hi)
    raise ValueError(f"unknown comparator {comparator!r}")


def payoff_matrix(contracts_df: pd.DataFrame, daily_df: pd.DataFrame,
                  season_df: pd.DataFrame) -> np.ndarray:
    """0/1 payouts, shape (N, n_contracts), column j = contracts_df row j.

    Rows are scenario_id 0..N-1 in order.
    """
    season = season_df.sort_values("scenario_id")
    n = len(season)
    daily_dates = pd.to_datetime(daily_df["date"]).dt.date
    win = (daily_dates.min(), daily_dates.max())
    period_cache: dict[tuple, np.ndarray] = {}
    # Lazily built (location, variable) -> {date: (N,) array} lookup for daily contracts.
    daily_cache: dict[tuple[str, str], pd.DataFrame] = {}

    out = np.zeros((n, len(contracts_df)), dtype=np.int8)
    for j, c in enumerate(contracts_df.itertuples(index=False)):
        hi = None if pd.isna(c.threshold_hi) else float(c.threshold_hi)
        start_c, end_c = pd.Timestamp(c.start).date(), pd.Timestamp(c.end).date()
        if c.variable in SEASON_VARS and (start_c, end_c) == win:
            x = season[f"{c.variable}_{c.location}"].to_numpy(dtype=float)
        elif c.variable in SEASON_VARS:
            key = (c.location, c.variable, start_c, end_c)
            if key not in period_cache:
                period_cache[key] = _period_total(daily_df, daily_dates, *key, n)
            x = period_cache[key]
        elif c.variable in DAILY_VARS:
            start = pd.Timestamp(c.start).date()
            end = pd.Timestamp(c.end).date()
            if start != end:
                raise ValueError(f"{c.contract_id}: daily-variable contracts must be single-day")
            key = (c.location, c.variable)
            if key not in daily_cache:
                mask = (daily_df["location"] == c.location).to_numpy()
                sub = pd.DataFrame({"scenario_id": daily_df["scenario_id"].to_numpy()[mask],
                                    "date": daily_dates.to_numpy()[mask],
                                    "v": daily_df[c.variable].to_numpy()[mask]})
                daily_cache[key] = sub.pivot(index="scenario_id", columns="date", values="v").sort_index()
            tbl = daily_cache[key]
            if start not in tbl.columns:
                raise ValueError(f"{c.contract_id}: date {start} not in simulated window")
            x = tbl[start].to_numpy(dtype=float)
        else:
            raise ValueError(f"{c.contract_id}: unknown variable {c.variable!r}")
        out[:, j] = _compare(x, c.comparator, float(c.threshold), hi)
    return out


def _period_total(daily_df: pd.DataFrame, dates: pd.Series, loc: str, var: str,
                  start: dt.date, end: dt.date, n: int) -> np.ndarray:
    """Season-type variable over a sub-period, computed from the daily table."""
    from farmerjoe.outputs.aggregate import HOT_DAY_F, gdd_daily
    m = ((daily_df["location"] == loc) & (dates >= start) & (dates <= end)).to_numpy()
    if not m.any():
        raise ValueError(f"no simulated days for {loc} in {start}..{end}")
    sub = daily_df.loc[m]
    if var == "rain_total_in":
        v = sub["precip_in"].to_numpy(float)
    elif var == "hot_days_95":
        v = (sub["tmax_f"].to_numpy(float) >= HOT_DAY_F).astype(float)
    else:
        v = gdd_daily(sub["tmax_f"].to_numpy(float), sub["tmin_f"].to_numpy(float))
    return np.bincount(sub["scenario_id"].to_numpy(), weights=v, minlength=n)


def contract_probs(contracts_df: pd.DataFrame, daily_df: pd.DataFrame,
                   season_df: pd.DataFrame) -> pd.DataFrame:
    """Fill p_model (fraction of scenarios paying) and p_se = sqrt(p(1-p)/N)."""
    pay = payoff_matrix(contracts_df, daily_df, season_df)
    n = pay.shape[0]
    p = pay.mean(axis=0)
    out = contracts_df.copy()
    out["p_model"] = p
    out["p_se"] = np.sqrt(p * (1 - p) / n)
    return out
