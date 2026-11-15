"""Fake data in the exact output schema, so teammates can build against it (Phase 0).

The numbers are plausible for central Illinois in July, but they are NOT a weather model:
fixed made-up parameters, a shared AR(1) latent field across locations, and a Gaussian
copula for rain. Do not use for anything except plumbing/integration tests.
"""
from __future__ import annotations

import datetime as dt
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from farmerjoe import MODEL_VERSION
from farmerjoe.outputs import schema
from farmerjoe.outputs.aggregate import basis_risk, season_totals
from farmerjoe.outputs.contracts import candidate_contracts, contract_probs
from farmerjoe.outputs.write import arrays_to_daily

# Made-up July parameters (deg F / inches).
_TMAX_MU, _TMAX_SD = 85.5, 5.5
_TMIN_MU, _TMIN_SD = 65.0, 4.0
_RHO_T, _RHO_R = 0.65, 0.35          # day-to-day persistence of latent fields
_CORR_T, _CORR_R = 0.85, 0.55        # cross-location correlation of innovations
_P_WET, _GAMMA_K, _GAMMA_THETA = 0.32, 0.75, 0.50

HONEST_LIMITS = [
    "Daily forecast skill fades after ~2 weeks; far-off windows are mostly climatology.",
    "Contracts settle at city stations; the farm's weather differs (basis risk, reported).",
    "Model covers weather (yield side) only, not crop prices.",
    "Educational tool, not financial advice.",
]


def _ar1_field(rng: np.random.Generator, n: int, d: int, n_loc: int,
               rho: float, corr: float) -> np.ndarray:
    """Stationary AR(1) latent field (N, D, L) with unit marginal variance and
    equicorrelated innovations across locations. Loops over days only."""
    cov = np.full((n_loc, n_loc), corr) + (1 - corr) * np.eye(n_loc)
    chol = np.linalg.cholesky(cov)
    eps = rng.standard_normal((n, d, n_loc)) @ chol.T
    z = np.empty_like(eps)
    z[:, 0] = eps[:, 0]
    scale = np.sqrt(1 - rho**2)
    for t in range(1, d):
        z[:, t] = rho * z[:, t - 1] + scale * eps[:, t]
    return z


def simulate_fake_arrays(n: int, d: int, n_loc: int, rng: np.random.Generator) -> dict[str, np.ndarray]:
    """Return tmax, tmin, precip arrays of shape (N, D, L)."""
    z_t = _ar1_field(rng, n, d, n_loc, _RHO_T, _CORR_T)
    z_n = _ar1_field(rng, n, d, n_loc, _RHO_T, _CORR_T)
    z_r = _ar1_field(rng, n, d, n_loc, _RHO_R, _CORR_R)
    loc_offset = np.linspace(0.0, -1.0, n_loc)  # stations slightly cooler than farm (made up)

    tmax = _TMAX_MU + loc_offset + _TMAX_SD * z_t
    tmin_z = 0.6 * z_t + 0.8 * z_n
    tmin = _TMIN_MU + loc_offset + _TMIN_SD * tmin_z
    tmin = np.minimum(tmin, tmax - 1.0)  # enforce tmin <= tmax

    # Gaussian copula with point mass at zero (same mapping planned for Phase 4).
    u = stats.norm.cdf(z_r)
    wet = u >= 1 - _P_WET
    q = np.clip((u - (1 - _P_WET)) / _P_WET, 1e-9, 1 - 1e-9)
    amt = stats.gamma.ppf(q, _GAMMA_K, scale=_GAMMA_THETA)
    precip = np.where(wet, np.maximum(np.round(amt, 2), 0.01), 0.0)
    return {"tmax_f": np.round(tmax, 1), "tmin_f": np.round(tmin, 1), "precip_in": precip}


def make_fake_outputs(
    N: int,
    seed: int,
    out_dir: str | Path,
    *,
    start: dt.date = dt.date(2027, 7, 1),
    end: dt.date = dt.date(2027, 7, 31),
    stations: list[str] | None = None,
    farm: tuple[float, float] = (40.1, -88.2),
    forecast_horizon_days: int = 14,
    contract_grid: dict | None = None,
    index_codes: list[str] | None = None,
    run_id: str | None = None,
    rng: np.random.Generator | None = None,
) -> Path:
    """Write all four output files with plausible random values in the exact schema.

    The forecast window for daily tmax contracts is taken as the first
    `forecast_horizon_days` days of the season (as if issued the day before start).
    Returns the output directory.
    """
    stations = stations or ["ORD", "MDW"]
    locations = ["farm", *stations, *(index_codes or [])]
    rng = rng if rng is not None else np.random.default_rng(seed)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    dates = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
    arrays = simulate_fake_arrays(N, len(dates), len(locations), rng)
    daily = arrays_to_daily(arrays, dates, locations)
    season = season_totals(arrays["tmax_f"], arrays["tmin_f"], arrays["precip_in"], locations)

    fc_days = dates[:forecast_horizon_days]
    contracts = candidate_contracts(stations, start, end, fc_days, contract_grid or {})
    contracts = contract_probs(contracts, daily, season)

    issue = start - dt.timedelta(days=1)
    meta = {
        "run_id": run_id or f"fake_{uuid.uuid4().hex[:8]}",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "forecast_issue_time": f"{issue.isoformat()}T00:00:00Z",
        "N": int(N),
        "seed": int(seed),
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "farm": {"lat": float(farm[0]), "lon": float(farm[1])},
        "stations": list(stations),
        "locations": locations,
        "model_version": MODEL_VERSION,
        "mode": "fake",
        "phase": 0,
        "fake_data": True,
        "calibration_scores": None,
        "basis_risk": basis_risk(season, stations),
        "notes": "FAKE DATA for integration only. Values are random, not a forecast.",
        "honest_limits": HONEST_LIMITS,
    }

    schema.write_daily(daily, out_dir / schema.DAILY_FILE, N)
    schema.write_season(season, out_dir / schema.SEASON_FILE, locations, N)
    schema.write_contracts(contracts, out_dir / schema.CONTRACTS_FILE, N)
    schema.write_meta(meta, out_dir / schema.META_FILE)
    return out_dir
