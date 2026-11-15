"""Monte Carlo engine, CLAUDE.md section 6.5.

Phase 1: climatology only, one location at a time (locations are independent here; the
Phase 2 latent-Gaussian model adds cross-location dependence).
  temperature: bivariate AR(1) on standardized anomalies (z_max, z_min), stationary start
  rain:        two-state Markov chain (p01, p11), stationary start; iid Gamma amounts
  interannual: if params["interannual"], add a per-season temperature offset and a
               per-season rain-amount multiplier (see climatology.fit_interannual)
Arrays are (N, D, L). We loop over days only (recursion), never over scenarios.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

from farmerjoe.model.climatology import WET_THRESHOLD_IN


def innovation_corr(rho1: float, rho2: float, target_corr: float) -> float:
    """Innovation correlation that gives stationary same-day correlation `target_corr`
    for two AR(1) series with coefficients rho1, rho2:
        corr_stat = c_e * sqrt((1-rho1^2)(1-rho2^2)) / (1 - rho1*rho2)
    """
    c = target_corr * (1 - rho1 * rho2) / np.sqrt((1 - rho1**2) * (1 - rho2**2))
    return float(np.clip(c, -0.999, 0.999))


def simulate_temperature(p: dict, n: int, d: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """(N, D) tmax, tmin for one location. tmin <= tmax is enforced by capping tmin."""
    r1, r2 = p["tmax_f_rho"], p["tmin_f_rho"]
    ce = innovation_corr(r1, r2, p["corr_tmax_tmin"])
    e1 = rng.standard_normal((n, d))
    e2 = ce * e1 + np.sqrt(1 - ce**2) * rng.standard_normal((n, d))
    z1, z2 = np.empty((n, d)), np.empty((n, d))
    # Day 0: draw from the stationary distribution (unit variance, same-day corr target).
    c0 = p["corr_tmax_tmin"]
    z1[:, 0] = e1[:, 0]
    z2[:, 0] = c0 * e1[:, 0] + np.sqrt(1 - c0**2) * rng.standard_normal(n)
    s1, s2 = np.sqrt(1 - r1**2), np.sqrt(1 - r2**2)
    for t in range(1, d):
        z1[:, t] = r1 * z1[:, t - 1] + s1 * e1[:, t]
        z2[:, t] = r2 * z2[:, t - 1] + s2 * e2[:, t]
    if p.get("interannual"):
        rc = p["tau_corr"]
        g1 = rng.standard_normal(n)
        g2 = rc * g1 + np.sqrt(1 - rc**2) * rng.standard_normal(n)
        tmax = p["tmax_f_mu"] + p["tmax_f_tau"] * g1[:, None] + p["tmax_f_sd_within"] * z1
        tmin = p["tmin_f_mu"] + p["tmin_f_tau"] * g2[:, None] + p["tmin_f_sd_within"] * z2
    else:
        tmax = p["tmax_f_mu"] + p["tmax_f_sd"] * z1
        tmin = p["tmin_f_mu"] + p["tmin_f_sd"] * z2
    return tmax, np.minimum(tmin, tmax)


def simulate_rain_markov(p: dict, n: int, d: int, rng: np.random.Generator) -> np.ndarray:
    """(N, D) daily precip for one location from a 2-state Markov chain + Gamma amounts."""
    p01, p11 = p["p01"], p["p11"]
    pi_wet = p01 / (1 - p11 + p01)  # stationary P(wet) of the chain
    u = rng.random((n, d))
    wet = np.empty((n, d), dtype=bool)
    wet[:, 0] = u[:, 0] < pi_wet
    for t in range(1, d):
        wet[:, t] = u[:, t] < np.where(wet[:, t - 1], p11, p01)
    amt = stats.gamma.rvs(p["gamma_k"], scale=p["gamma_theta"], size=(n, d), random_state=rng)
    if p.get("interannual") and p.get("rain_amount_logsd", 0) > 0:
        s = p["rain_amount_logsd"]
        amt = amt * np.exp(s * rng.standard_normal(n) - s**2 / 2)[:, None]  # mean-1 season factor
    # A draw (or the season factor) can fall below the 0.01" wet threshold; floor it so
    # wet days stay wet.
    return np.where(wet, np.maximum(amt, WET_THRESHOLD_IN), 0.0)


def simulate_climatology(params: list[dict], n: int, d: int,
                         rng: np.random.Generator) -> dict[str, np.ndarray]:
    """Simulate N seasons of D days for each location's params -> (N, D, L) arrays."""
    tx, tn, pr = [], [], []
    for p in params:
        a, b = simulate_temperature(p, n, d, rng)
        tx.append(a)
        tn.append(b)
        pr.append(simulate_rain_markov(p, n, d, rng))
    return {"tmax_f": np.stack(tx, -1), "tmin_f": np.stack(tn, -1), "precip_in": np.stack(pr, -1)}
