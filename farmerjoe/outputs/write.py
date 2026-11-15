"""Assemble and write a full run (all four contract files) from simulated arrays."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from farmerjoe.outputs import schema
from farmerjoe.outputs.aggregate import basis_risk, season_totals
from farmerjoe.outputs.contracts import candidate_contracts, contract_probs


def arrays_to_daily(arrays: dict[str, np.ndarray], dates: list[dt.date],
                    locations: list[str]) -> pd.DataFrame:
    """(N, D, L) arrays -> long scenarios_daily frame, ordered scenario, date, location.
    Temperatures rounded to 0.1°F and precip to 0.001 in (below obs precision)."""
    n, d, n_loc = arrays["tmax_f"].shape
    sid, di, li = np.meshgrid(np.arange(n), np.arange(d), np.arange(n_loc), indexing="ij")
    return pd.DataFrame({
        "scenario_id": sid.ravel().astype(np.int32),
        "date": np.asarray(dates, dtype=object)[di.ravel()],
        "location": np.asarray(locations, dtype=object)[li.ravel()],
        "tmax_f": arrays["tmax_f"].ravel().astype(np.float32),
        "tmin_f": arrays["tmin_f"].ravel().astype(np.float32),
        "precip_in": arrays["precip_in"].ravel().astype(np.float32),
    })


def write_run(out_dir: str | Path, arrays: dict[str, np.ndarray], dates: list[dt.date],
              locations: list[str], stations: list[str] | dict[str, list[str]],
              forecast_days: list[dt.date], contract_grid: dict, meta: dict[str, Any],
              extra_meta: Callable[[pd.DataFrame, pd.DataFrame, pd.DataFrame], dict] | None = None,
              ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate, price contracts, fill basis risk, validate and write all four files.

    `stations` is a list of codes or {code: markets}. `meta` must hold every META_REQUIRED_KEY
    except basis_risk (filled here). `extra_meta(daily, season, contracts)` may add keys
    (e.g., hedge_diagnostics) before the single validated write. Returns (season, contracts).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    n = arrays["tmax_f"].shape[0]
    # Season totals from the same float32 values that are written to the daily file.
    a32 = {k: v.astype(np.float32).astype(np.float64) for k, v in arrays.items()}
    daily = arrays_to_daily(arrays, dates, locations)
    season = season_totals(a32["tmax_f"], a32["tmin_f"], a32["precip_in"], locations)
    contracts = candidate_contracts(stations, dates[0], dates[-1], forecast_days, contract_grid)
    contracts = contract_probs(contracts, daily, season)

    meta = dict(meta, locations=list(locations))
    meta["basis_risk"] = basis_risk(season, list(stations)) if "farm" in locations else {}
    if extra_meta is not None:
        meta.update(extra_meta(daily, season, contracts))
    schema.write_daily(daily, out_dir / schema.DAILY_FILE, n)
    schema.write_season(season, out_dir / schema.SEASON_FILE, locations, n)
    schema.write_contracts(contracts, out_dir / schema.CONTRACTS_FILE, n)
    schema.write_meta(meta, out_dir / schema.META_FILE)
    return season, contracts
