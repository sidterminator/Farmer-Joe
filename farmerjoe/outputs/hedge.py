"""Hedge effectiveness + hedge_diagnostics (CLAUDE.md 7). Shared with the optimizer.

max_hedge_effectiveness = out-of-sample R^2 of OLS(y ~ 1 + payoffs): fit on a random half of
scenarios, score on the other half, so many correlated binary contracts can't overstate it.
It is the largest share of Var(y) any linear contract position could remove.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def hedge_effectiveness(y: np.ndarray, payoffs: np.ndarray, rng: np.random.Generator,
                        train_frac: float = 0.5) -> float | None:
    """Out-of-sample R^2 in [0, 1] (None if y has no variance or no usable payoffs)."""
    y = np.asarray(y, float)
    X = np.asarray(payoffs, float)
    if X.ndim == 1:
        X = X[:, None]
    X = X[:, X.std(axis=0) > 0]
    if y.std() == 0 or X.shape[1] == 0:
        return None
    idx = rng.permutation(len(y))
    k = int(len(y) * train_frac)
    tr, te = idx[:k], idx[k:]
    A = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(A[tr], y[tr], rcond=None)
    resid = y[te] - A[te] @ beta
    sst = np.sum((y[te] - y[te].mean()) ** 2)
    return float(np.clip(1 - np.sum(resid**2) / sst, 0.0, 1.0))


def hedge_diagnostics(season: pd.DataFrame, contracts: pd.DataFrame, payoffs: np.ndarray,
                      station_info: list[dict[str, Any]], rng: np.random.Generator) -> dict[str, Any]:
    """Screening diagnostics for each farm season variable (see CLAUDE.md 7)."""
    out: dict[str, Any] = {"method": "out-of-sample OLS R^2 (50/50 scenario split) of farm season "
                                     "variable on contract payoffs; screening proxy for revenue",
                           "distance_km": {s["code"]: s["distance_km"] for s in station_info}}
    codes = [s["code"] for s in station_info]
    for var in ("rain_total_in", "hot_days_95", "gdd"):
        y = season[f"{var}_farm"].to_numpy(float)
        if y.std() == 0:
            out[var] = {"note": "no variance at the farm (e.g., hot days never occur in this window)"}
            continue
        by_station = {}
        for c in codes:
            cols = (contracts["location"] == c).to_numpy()
            by_station[c] = None if not cols.any() else round(hedge_effectiveness(y, payoffs[:, cols], rng) or 0.0, 4)
        r2 = []
        for j in range(payoffs.shape[1]):
            x = payoffs[:, j]
            r2.append(0.0 if x.std() == 0 else float(np.corrcoef(y, x)[0, 1] ** 2))
        j = int(np.argmax(r2)) if r2 else None
        corr = {}
        for c in codes:
            x = season[f"{var}_{c}"].to_numpy(float)
            corr[c] = round(float(np.corrcoef(y, x)[0, 1]), 4) if x.std() > 0 else None
        he = hedge_effectiveness(y, payoffs, rng)
        out[var] = {"max_hedge_effectiveness": None if he is None else round(he, 4),
                    "by_station": by_station,
                    "best_single_contract": None if j is None else
                    {"contract_id": contracts["contract_id"].iloc[j], "r2": round(r2[j], 4)},
                    "corr_with_station": corr}
    return out
