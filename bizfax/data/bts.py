"""BTS on-time performance loader (US airports; passenger flights as a hub-delay proxy).

Download monthly CSVs from https://www.transtats.bts.gov/ (Reporting Carrier On-Time
Performance) into data/raw/bts/. Both the legacy (FlightDate/Origin/DepDelay) and
newer (FL_DATE/ORIGIN/DEP_DELAY) column styles are accepted.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

_ALIASES = {
    "FlightDate": "date", "FL_DATE": "date",
    "Origin": "origin", "ORIGIN": "origin",
    "DepDelay": "dep_delay", "DEP_DELAY": "dep_delay",
    "Cancelled": "cancelled", "CANCELLED": "cancelled",
}


def load(folder: str | Path = "data/raw/bts", airports: tuple[str, ...] = ("CVG", "SDF", "MEM", "JFK")) -> pd.DataFrame:
    frames = []
    for f in sorted(Path(folder).glob("*.csv")):
        df = pd.read_csv(f, usecols=lambda c: c in _ALIASES, low_memory=False).rename(columns=_ALIASES)
        frames.append(df[df["origin"].isin(airports)])
    if not frames:
        raise FileNotFoundError(f"No BTS CSVs in {folder}")
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def daily_delay_rate(df: pd.DataFrame, threshold_min: int = 60) -> pd.DataFrame:
    """Per airport-day: share of departures delayed >= threshold or cancelled.

    This is the target the weather->delay model is fit on.
    """
    bad = (df["dep_delay"].fillna(0) >= threshold_min) | (df["cancelled"] == 1)
    return (df.assign(bad=bad).groupby(["origin", "date"])["bad"]
              .agg(delay_rate="mean", flights="size").reset_index())
