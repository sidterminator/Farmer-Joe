"""Climatology sanity checks: simulated vs historical season distributions (CLAUDE.md 8)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

SEASON_VARS = ("rain_total_in", "hot_days_95", "gdd")


def bootstrap_ci(x: np.ndarray, stat, rng: np.random.Generator, n_boot: int = 4000,
                 level: float = 0.90) -> tuple[float, float]:
    """Percentile bootstrap CI for stat(x) over years (x resampled with replacement)."""
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    vals = np.apply_along_axis(stat, 1, x[idx])
    a = (1 - level) / 2
    return float(np.quantile(vals, a)), float(np.quantile(vals, 1 - a))


def compare_season(sim: pd.DataFrame, hist: pd.DataFrame, loc: str,
                   rng: np.random.Generator, tol: float = 0.10) -> pd.DataFrame:
    """Per season variable: sim vs hist mean/sd, relative error, a 90% bootstrap CI for the
    historical value (sampling noise from few years), and a KS p-value.

    `within_tol` = |rel err| <= tol (the CLAUDE.md ~10% target).
    `within_ci`  = simulated value falls inside the historical 90% CI.
    """
    rows = []
    for v in SEASON_VARS:
        s = sim[f"{v}_{loc}"].to_numpy(dtype=float)
        h = hist[v].to_numpy(dtype=float)
        for name, fn in (("mean", np.mean), ("sd", lambda a: np.std(a, ddof=1))):
            sv, hv = float(fn(s)), float(fn(h))
            lo, hi = bootstrap_ci(h, fn, rng)
            rel = sv / hv - 1 if hv != 0 else np.nan
            rows.append(dict(variable=v, stat=name, sim=sv, hist=hv, rel_err=rel,
                             hist_ci90_lo=lo, hist_ci90_hi=hi,
                             within_tol=bool(abs(rel) <= tol), within_ci=bool(lo <= sv <= hi)))
        rows[-1]["ks_p"] = rows[-2]["ks_p"] = float(stats.ks_2samp(s, h).pvalue)
    return pd.DataFrame(rows)


def correlation_check(sim: pd.DataFrame, hist: dict[str, pd.DataFrame], pairs: list[tuple[str, str, str]],
                      variables: tuple[str, ...], rng: np.random.Generator, tol: float = 0.10,
                      n_boot: int = 4000) -> pd.DataFrame:
    """Simulated vs historical correlation of season variables for location pairs.

    pairs: (loc_a, loc_b, kind). hist[loc]: per-year season totals (historical_season_totals).
    Historical correlation uses years complete at both locations; its 90% bootstrap range
    (resampling years) shows how much 20-25 years can pin a correlation down.
    """
    rows = []
    for a, b, kind in pairs:
        m = hist[a].merge(hist[b], on="year", suffixes=("_a", "_b"))
        for v in variables:
            x, y = m[f"{v}_a"].to_numpy(float), m[f"{v}_b"].to_numpy(float)
            sa, sb = sim[f"{v}_{a}"].to_numpy(float), sim[f"{v}_{b}"].to_numpy(float)
            row = dict(pair=f"{a}–{b}", kind=kind, variable=v, n_years=len(m))
            if len(m) < 8 or x.std() == 0 or y.std() == 0 or sa.std() == 0 or sb.std() == 0:
                row.update(hist_corr=np.nan, sim_corr=np.nan, diff=np.nan, ci_lo=np.nan, ci_hi=np.nan,
                           within_tol=None, within_ci=None,
                           note="too few events to define a correlation (e.g., hot days never occur)")
                rows.append(row)
                continue
            h = float(np.corrcoef(x, y)[0, 1])
            s = float(np.corrcoef(sa, sb)[0, 1])
            idx = rng.integers(0, len(m), size=(n_boot, len(m)))
            bx, by = x[idx], y[idx]
            bx = bx - bx.mean(1, keepdims=True)
            by = by - by.mean(1, keepdims=True)
            den = np.sqrt((bx**2).sum(1) * (by**2).sum(1))
            bc = np.where(den > 0, (bx * by).sum(1) / np.where(den > 0, den, 1), np.nan)
            lo, hi = np.nanquantile(bc, [0.05, 0.95])
            row.update(hist_corr=h, sim_corr=s, diff=s - h, ci_lo=float(lo), ci_hi=float(hi),
                       within_tol=bool(abs(s - h) <= tol), within_ci=bool(lo <= s <= hi), note="")
            rows.append(row)
    return pd.DataFrame(rows)
