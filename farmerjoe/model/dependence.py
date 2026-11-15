"""Latent-Gaussian dependence across locations + joint simulation (CLAUDE.md 6.3).

Per location l:
  temperature: tmax = mu + tau*g + sd_within*z,  same for tmin
               z  = within-season AR(1) latent (rho per variable), unit variance
               g  = season-level offset ~ N(0, 1) (the interannual component)
  rain:        r  = sqrt(1-lam)*AR(1) + sqrt(lam)*season latent (lag-1 corr matches p11)
               u = Phi(r); dry if u < 1 - p_wet; else amount = Gamma^-1(Phi(w); k, theta) * M
               w  = separate AR(1) amount latent with rain_amount_rho (fit per location so
                    season-total variance matches history); spatial corr R_rain (as for
                    occurrence). R_amount (corr of amount normal scores on days wet at both
                    locations) is kept as a diagnostic only: on gridded data it is dominated
                    by drizzle noise and understates how big storms co-occur.
                    AR(1) innovations are built so the same-day spatial correlation holds
                    exactly even when locations have different persistence.
               M  = season rain-amount multiplier, LogNormal(-s^2/2, s^2)
Across locations (all estimated on the fit years, pairwise-complete):
  R_year, R_within (2L x 2L, order tmax_1..L, tmin_1..L) are solved per pair from two observed
           correlations, daily anomalies C and season means M (a season mean = offset + the
           average of the daily wiggles, so M is NOT the offset correlation by itself):
             C_ij sd_i sd_j        = tau_i tau_j R_year + sdw_i sdw_j R_within
             M_ij sqrt(Vm_i Vm_j)  = tau_i tau_j R_year + sdw_i sdw_j R_within * f_ij / D
           with Vm = tau^2 + sdw^2 f/D and f = AR(1) variance factor of a D-day mean.
  R_rain   same-day rain-latent corr, solved per pair so P(both wet) matches history
  R_rain_year  corr of the season-level rain latents (wet/dry summers), solved per pair with
           a pilot simulation so simulated season-rain correlations match history
           (solve_rain_year_corr); R_rain_within follows from R_rain and R_rain_year.
AR(1) innovations get corr E_ij = R_ij (1 - rho_i rho_j) / sqrt((1-rho_i^2)(1-rho_j^2)), so the
stationary same-day corr equals R. Every matrix is projected to the nearest valid correlation
matrix (eigenvalue clipping) before use.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from farmerjoe.model.climatology import (WET_THRESHOLD_IN, ar1_from, day_index, detrend, mu_curve,
                                         rain_day_arrays, select_window, solve_latent_corr, within_rhos)

TEMP_VARS = ("tmax_f", "tmin_f")


def nearest_corr(a: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    """Symmetric, positive-definite, unit-diagonal matrix closest-ish to `a` (eigen-clip)."""
    a = (np.asarray(a, float) + np.asarray(a, float).T) / 2
    np.fill_diagonal(a, 1.0)
    w, v = np.linalg.eigh(a)
    a = (v * np.maximum(w, eps)) @ v.T
    d = np.sqrt(np.diag(a))
    a = a / np.outer(d, d)
    np.fill_diagonal(a, 1.0)
    return a


def innovation_corr_matrix(r: np.ndarray, rho: np.ndarray) -> np.ndarray:
    """AR(1) innovation correlations giving stationary same-day correlation `r`."""
    num = r * (1 - np.outer(rho, rho))
    den = np.sqrt(np.outer(1 - rho**2, 1 - rho**2))
    return nearest_corr(np.clip(num / den, -0.999, 0.999))


def _pairwise_corr(df: pd.DataFrame) -> np.ndarray:
    c = df.corr(min_periods=10).to_numpy()
    return np.where(np.isfinite(c), c, 0.0)


def fit_dependence(obs: dict[str, pd.DataFrame], params: dict[str, dict[str, Any]],
                   start: dt.date, end: dt.date, years: tuple[int, int]) -> dict[str, Any]:
    """Estimate the cross-location matrices from each location's history (window days only)."""
    locs = list(obs)
    n_exp = (end - start).days + 1
    z_cols, wet_cols, ym_cols, tot_cols, ns_cols = {}, {}, {}, {}, {}
    for loc in locs:
        p = params[loc]
        o = detrend(obs[loc], p["trend"]) if p.get("trend") else obs[loc]
        w = select_window(o, start, end, 0, years).set_index("date")
        t = day_index(w.index, start)
        for v in TEMP_VARS:
            coef = p.get(f"{v}_mu_poly")
            mu_t = np.polyval(coef, t) if coef else p[f"{v}_mu"]
            z_cols[f"{v}|{loc}"] = (w[v] - mu_t) / p[f"{v}_sd"]
            g = w.groupby("year")[v].agg(["mean", "count"])
            ym_cols[f"{v}|{loc}"] = g["mean"].where(g["count"] >= 0.9 * n_exp)
        wet_cols[loc] = (w["precip_in"] >= WET_THRESHOLD_IN).astype(float).where(w["precip_in"].notna())
        amt = w["precip_in"].where(w["precip_in"] >= WET_THRESHOLD_IN)
        ns_cols[loc] = pd.Series(stats.norm.ppf(np.clip(stats.gamma.cdf(amt, p["gamma_k"], scale=p["gamma_theta"]),
                                                        1e-6, 1 - 1e-6)), index=w.index).where(amt.notna())
        g = w.groupby("year")["precip_in"].agg(["sum", "count"])
        tot_cols[loc] = g["sum"].where(g["count"] == n_exp)

    order = [f"{v}|{loc}" for v in TEMP_VARS for loc in locs]
    C = _pairwise_corr(pd.DataFrame(z_cols)[order])
    M = _pairwise_corr(pd.DataFrame(ym_cols)[order])
    sd = np.array([params[k.split("|")[1]][f"{k.split('|')[0]}_sd"] for k in order])
    rho = np.array([params[k.split("|")[1]][f"{k.split('|')[0]}_rho"] for k in order])
    has_ia = [params[k.split("|")[1]].get("interannual", False) for k in order]
    tau = np.array([params[k.split("|")[1]][f"{k.split('|')[0]}_tau"] if ia else 0.0
                    for k, ia in zip(order, has_ia)])
    sdw = np.sqrt(np.maximum(sd**2 - tau**2, 1e-9))
    R_year, R_within = solve_year_within(C, M, sd, tau, sdw, rho, n_exp)
    wet = pd.DataFrame(wet_cols)[locs]
    L = len(locs)
    R_rain = np.eye(L)
    for i in range(L):
        for j in range(i + 1, L):
            both = wet[[locs[i], locs[j]]].dropna()
            if len(both) < 30:
                continue
            pi_, pj_ = params[locs[i]]["p_wet"], params[locs[j]]["p_wet"]
            # joint frequency rescaled to the fitted marginals (pairwise days may differ)
            pb = float((both.iloc[:, 0] * both.iloc[:, 1]).mean())
            pb *= (pi_ * pj_) / max(both.iloc[:, 0].mean() * both.iloc[:, 1].mean(), 1e-9)
            R_rain[i, j] = R_rain[j, i] = solve_latent_corr(pi_, pj_, min(pb, min(pi_, pj_)))
    R_rain = nearest_corr(R_rain)
    ns = pd.DataFrame(ns_cols)[locs]
    R_amount = np.eye(L)
    for i in range(L):
        for j in range(i + 1, L):
            both = ns[[locs[i], locs[j]]].dropna()
            R_amount[i, j] = R_amount[j, i] = (float(np.clip(both.corr().iloc[0, 1], -0.95, 0.95))
                                               if len(both) >= 30 else R_rain[i, j])
    R_amount = nearest_corr(R_amount)

    tot = pd.DataFrame(tot_cols)[locs]
    ns = tot.apply(lambda s: pd.Series(stats.norm.ppf((s.rank() - 0.5) / s.notna().sum()), index=s.index))
    R_mult = nearest_corr(_pairwise_corr(ns))
    return {"locations": locs, "temp_order": order, "R_within": R_within.tolist(),
            "R_year": R_year.tolist(), "R_rain": R_rain.tolist(), "R_amount": R_amount.tolist(),
            "R_mult": R_mult.tolist()}


def solve_year_within(C: np.ndarray, M: np.ndarray, sd: np.ndarray, tau: np.ndarray,
                      sdw: np.ndarray, rho: np.ndarray, d: int) -> tuple[np.ndarray, np.ndarray]:
    """Per pair, solve the two linear equations in the module docstring for (R_year, R_within).
    Where a location has no season offset (tau ~ 0) the daily correlation is used directly."""
    from farmerjoe.model.climatology import ar1_mean_var_factor
    m = len(sd)
    f = np.array([[ar1_mean_var_factor(np.sqrt(max(rho[i] * rho[j], 0.0)), d) for j in range(m)] for i in range(m)])
    g = f / d
    vm = tau**2 + sdw**2 * np.diag(g)
    a1 = np.outer(tau, tau)
    b1 = np.outer(sdw, sdw)
    cov_daily = C * np.outer(sd, sd)
    cov_mean = M * np.sqrt(np.outer(vm, vm))
    with np.errstate(divide="ignore", invalid="ignore"):
        Rw = (cov_daily - cov_mean) / (b1 * (1 - g))
        Ry = (cov_mean - b1 * Rw * g) / a1
    tiny = a1 < 1e-6
    Rw = np.where(tiny, C, Rw)
    Ry = np.where(tiny | ~np.isfinite(Ry), M, Ry)
    return nearest_corr(np.clip(Ry, -0.999, 0.999)), nearest_corr(np.clip(Rw, -0.999, 0.999))


def latent_to_rain(z: np.ndarray, p_wet, k, theta, mult=None, w=None) -> np.ndarray:
    """Gaussian copula with point mass at 0: latent z -> daily precip (inches).
    Occurrence: wet if Phi(z) >= 1 - p_wet. Amount quantile: Phi(w) if an amount latent `w`
    is given, else the conditional quantile of z itself. Parameters broadcast against the
    last axis (locations) or are scalars."""
    u = stats.norm.cdf(z)
    dry = u < 1 - p_wet
    if w is None:
        q = (u - (1 - p_wet)) / p_wet
    else:
        q = stats.norm.cdf(w)
    amt = stats.gamma.ppf(np.clip(q, 1e-9, 1 - 1e-9), k, scale=theta)
    if mult is not None:
        amt = amt * mult
    return np.where(dry, 0.0, np.maximum(amt, WET_THRESHOLD_IN))


def _ar1(n: int, d: int, rho: np.ndarray, R: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """(n, d, m) stationary AR(1) with per-component rho and same-day correlation R."""
    m = len(rho)
    chol_r = np.linalg.cholesky(nearest_corr(R))
    chol_e = np.linalg.cholesky(innovation_corr_matrix(np.asarray(R), rho))
    z = np.empty((n, d, m))
    z[:, 0] = rng.standard_normal((n, m)) @ chol_r.T
    s = np.sqrt(1 - rho**2)
    for t in range(1, d):
        z[:, t] = rho * z[:, t - 1] + s * (rng.standard_normal((n, m)) @ chol_e.T)
    return z


def simulate_joint(params: dict[str, dict[str, Any]], dep: dict[str, Any], n: int, d: int,
                   year: int, rng: np.random.Generator) -> dict[str, np.ndarray]:
    """Jointly simulate all locations -> {tmax_f, tmin_f, precip_in}: (N, D, L) arrays,
    location axis in dep['locations'] order. `year` sets trend-adjusted means."""
    locs = dep["locations"]
    L = len(locs)
    P = [params[l] for l in locs]
    rho_t = np.array([p[f"{v}_rho"] for v in TEMP_VARS for p in P])
    z = _ar1(n, d, rho_t, np.asarray(dep["R_within"]), rng)            # (n, d, 2L)
    g = rng.standard_normal((n, 2 * L)) @ np.linalg.cholesky(nearest_corr(dep["R_year"])).T

    out = {}
    for i, v in enumerate(TEMP_VARS):
        sl = slice(i * L, (i + 1) * L)
        mu = np.stack([mu_curve(p, v, year, d) for p in P], axis=-1)    # (d, L)
        tau = np.array([p.get(f"{v}_tau", 0.0) if p.get("interannual") else 0.0 for p in P])
        sdw = np.array([p[f"{v}_sd_within"] if p.get("interannual") else p[f"{v}_sd"] for p in P])
        out[v] = mu + tau * g[:, None, sl] + sdw * z[:, :, sl]
    out["tmin_f"] = np.minimum(out["tmin_f"], out["tmax_f"])

    # Rain: total latent = sqrt(1-lam) * within-season AR(1) + sqrt(lam) * season latent gr,
    # for both occurrence (z) and amounts (w); season multiplier (if any) driven by gr too.
    lam = np.array([p.get("rain_year_share", 0.0) for p in P])
    rw = np.array([p.get("rain_rho_within", p["rain_rho"]) for p in P])
    aw = np.array([p.get("rain_amount_rho", 0.0) for p in P])
    R_w = np.asarray(dep.get("R_rain_within", dep["R_rain"]))
    gr = rng.standard_normal((n, L)) @ np.linalg.cholesky(nearest_corr(dep.get("R_rain_year", np.eye(L)))).T
    zr = np.sqrt(1 - lam) * _ar1(n, d, rw, R_w, rng) + np.sqrt(lam) * gr[:, None, :]
    w = np.sqrt(1 - lam) * _ar1(n, d, aw, R_w, rng) + np.sqrt(lam) * gr[:, None, :]
    s = np.array([p.get("rain_amount_logsd", 0.0) if p.get("interannual") else 0.0 for p in P])
    mult = np.exp(s * gr - s**2 / 2)[:, None, :]
    arr = [rain_day_arrays(p, d) for p in P]
    pw = np.stack([a[0] for a in arr], -1)
    k = np.stack([a[1] for a in arr], -1)
    th = np.stack([a[2] for a in arr], -1)
    out["precip_in"] = latent_to_rain(zr, pw, k, th, mult, w)
    return out


def _corr_pair(e_i: np.ndarray, e_j: np.ndarray, r: float) -> np.ndarray:
    """Standard normals for location j correlated r with location i (same shape)."""
    return r * e_i + np.sqrt(max(1 - r**2, 0.0)) * e_j


def _ar1_pair(e_i, e_j, rho_i, rho_j, r):
    """Two stationary AR(1) series with same-day correlation r (innovations solved)."""
    c = float(innovation_corr_matrix(np.array([[1, r], [r, 1]]), np.array([rho_i, rho_j]))[0, 1])
    x_i = ar1_from(e_i, rho_i)
    ej = _corr_pair(e_i, e_j, c)
    ej[:, 0] = _corr_pair(e_i[:, :1], e_j[:, :1], r)[:, 0]      # stationary start
    x_j = np.empty_like(ej)
    x_j[:, 0] = ej[:, 0]
    s = np.sqrt(1 - rho_j**2)
    for t in range(1, ej.shape[1]):
        x_j[:, t] = rho_j * x_j[:, t - 1] + s * ej[:, t]
    return x_i, x_j


def within_rain_corr(R_rain: np.ndarray, R_year: np.ndarray, lam: np.ndarray) -> np.ndarray:
    """Same-day corr of the within-season rain latents, given total same-day corr R_rain
    (from co-occurrence) = sqrt((1-l_i)(1-l_j)) R_w + sqrt(l_i l_j) R_year."""
    a = np.sqrt(np.outer(1 - lam, 1 - lam))
    b = np.sqrt(np.outer(lam, lam))
    return nearest_corr(np.clip((R_rain - b * R_year) / a, -0.999, 0.999))


def solve_rain_year_corr(params: dict[str, dict[str, Any]], dep: dict[str, Any],
                         hist_totals: dict[str, pd.Series], d: int, rng: np.random.Generator,
                         n: int = 2500, grid: np.ndarray | None = None) -> dict[str, Any]:
    """Correlation of the season-level rain latents (R_rain_year), solved per pair with a small
    pilot simulation (common random numbers) so the simulated season-rain correlation matches
    history. Pairs where either location has no season component keep 0 (unused)."""
    grid = np.linspace(-0.4, 0.99, 12) if grid is None else grid
    locs = dep["locations"]
    L = len(locs)
    P = [params[l] for l in locs]
    lam = np.array([p.get("rain_year_share", 0.0) for p in P])
    s = np.array([p.get("rain_amount_logsd", 0.0) for p in P])
    R_rain = np.asarray(dep["R_rain"])
    tot = pd.DataFrame(hist_totals)[locs]
    arrays = [rain_day_arrays(p, d) for p in P]
    Ry = np.eye(L)
    from farmerjoe.model.dependence import latent_to_rain as _ltr
    for i in range(L):
        for j in range(i + 1, L):
            pair = tot[[locs[i], locs[j]]].dropna()
            if lam[i] < 1e-3 or lam[j] < 1e-3 or len(pair) < 10:
                continue
            c_obs = float(pair.corr().iloc[0, 1])
            ez_i, ez_j, ew_i, ew_j = (rng.standard_normal((n, d)) for _ in range(4))
            g_i, g_j = rng.standard_normal(n), rng.standard_normal(n)
            rw_i, aw_i = within_rhos(P[i], lam[i])
            rw_j, aw_j = within_rhos(P[j], lam[j])
            curve = []
            for r in grid:
                rw = float(np.clip((R_rain[i, j] - np.sqrt(lam[i] * lam[j]) * r) /
                                   np.sqrt((1 - lam[i]) * (1 - lam[j])), -0.99, 0.99))
                zi, zj = _ar1_pair(ez_i, ez_j, rw_i, rw_j, rw)
                wi, wj = _ar1_pair(ew_i, ew_j, aw_i, aw_j, rw)
                gj = _corr_pair(g_i, g_j, r)
                Ti = _ltr(np.sqrt(1 - lam[i]) * zi + np.sqrt(lam[i]) * g_i[:, None], *arrays[i],
                          np.exp(s[i] * g_i - s[i] ** 2 / 2)[:, None],
                          np.sqrt(1 - lam[i]) * wi + np.sqrt(lam[i]) * g_i[:, None]).sum(1)
                Tj = _ltr(np.sqrt(1 - lam[j]) * zj + np.sqrt(lam[j]) * gj[:, None], *arrays[j],
                          np.exp(s[j] * gj - s[j] ** 2 / 2)[:, None],
                          np.sqrt(1 - lam[j]) * wj + np.sqrt(lam[j]) * gj[:, None]).sum(1)
                curve.append(np.corrcoef(Ti, Tj)[0, 1])
            curve = np.maximum.accumulate(np.array(curve))
            Ry[i, j] = Ry[j, i] = float(np.interp(c_obs, curve, grid))
    Ry = nearest_corr(Ry)
    dep = dict(dep)
    dep["R_rain_year"] = Ry.tolist()
    dep["R_rain_within"] = within_rain_corr(R_rain, Ry, lam).tolist()
    return dep
