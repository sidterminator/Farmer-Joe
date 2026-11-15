"""Known-truth recovery tests. (EMOS recovery is added in Phase 4.)"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from farmerjoe.model.climatology import (fit_climatology, markov_gamma_total_moments,
                                         ar1_mean_var_factor)

# k, theta chosen so < 2% of Gamma mass is below the 0.01" wet threshold; for very small k
# (ORD July k~0.6) flooring tiny amounts biases the plain gamma.fit k upward (~10%).
TRUE = dict(p01=0.25, p11=0.50, k=1.2, theta=0.35, rho=0.6, mu=84.0, sd=6.5)
YEARS = (1700, 2099)  # 400 synthetic Julys -> tight tolerances
START, END = dt.date(2027, 7, 1), dt.date(2027, 7, 31)


def _synthetic_obs(seed: int = 0) -> pd.DataFrame:
    """Independent generator (not the simulator under test): Markov rain + Gamma amounts,
    AR(1) tmax, tmin = tmax - 19 + noise."""
    rng = np.random.default_rng(seed)
    n_y, d = YEARS[1] - YEARS[0] + 1, 31
    pi = TRUE["p01"] / (1 - TRUE["p11"] + TRUE["p01"])
    wet = np.zeros((n_y, d), bool)
    wet[:, 0] = rng.random(n_y) < pi
    z = np.zeros((n_y, d))
    z[:, 0] = rng.standard_normal(n_y)
    for t in range(1, d):
        wet[:, t] = rng.random(n_y) < np.where(wet[:, t - 1], TRUE["p11"], TRUE["p01"])
        z[:, t] = TRUE["rho"] * z[:, t - 1] + np.sqrt(1 - TRUE["rho"] ** 2) * rng.standard_normal(n_y)
    amt = rng.gamma(TRUE["k"], TRUE["theta"], (n_y, d))
    precip = np.where(wet, np.maximum(amt, 0.01), 0.0)
    tmax = TRUE["mu"] + TRUE["sd"] * z
    tmin = tmax - 19 + rng.normal(0, 3, (n_y, d))
    dates = [dt.date(y, 7, 1) + dt.timedelta(days=i) for y in range(YEARS[0], YEARS[1] + 1) for i in range(d)]
    return pd.DataFrame({"date": dates, "tmax_f": tmax.ravel(), "tmin_f": tmin.ravel(),
                         "precip_in": precip.ravel()})


@pytest.fixture(scope="module")
def fitted():
    return fit_climatology(_synthetic_obs(), START, END, YEARS, buffer_days=0)


def test_markov_recovered(fitted):
    assert fitted["p01"] == pytest.approx(TRUE["p01"], abs=0.02)
    assert fitted["p11"] == pytest.approx(TRUE["p11"], abs=0.03)


def test_gamma_recovered(fitted):
    assert fitted["gamma_k"] == pytest.approx(TRUE["k"], rel=0.08)
    assert fitted["gamma_theta"] == pytest.approx(TRUE["theta"], rel=0.10)


def test_temperature_recovered(fitted):
    assert fitted["tmax_f_mu"] == pytest.approx(TRUE["mu"], abs=0.3)
    assert fitted["tmax_f_sd"] == pytest.approx(TRUE["sd"], rel=0.05)
    assert fitted["tmax_f_rho"] == pytest.approx(TRUE["rho"], abs=0.04)


def test_rho_does_not_chain_years(fitted):
    """Lag-1 pairs are within-year only: 30 pairs per 31-day July, none across Jul31->Jul1."""
    n_years = YEARS[1] - YEARS[0] + 1
    assert fitted["n_transitions"] == n_years * 30


def test_markov_gamma_moments_match_monte_carlo():
    rng = np.random.default_rng(3)
    n, d = 200_000, 31
    p01, p11, k, th = 0.26, 0.44, 0.6, 0.68
    pi = p01 / (1 - p11 + p01)
    wet = np.empty((n, d), bool)
    wet[:, 0] = rng.random(n) < pi
    for t in range(1, d):
        wet[:, t] = rng.random(n) < np.where(wet[:, t - 1], p11, p01)
    tot = np.where(wet, rng.gamma(k, th, (n, d)), 0).sum(1)
    m, v = markov_gamma_total_moments(p01, p11, k, th, d)
    assert tot.mean() == pytest.approx(m, rel=0.01)
    assert tot.var() == pytest.approx(v, rel=0.02)


def test_ar1_mean_var_factor():
    rng = np.random.default_rng(4)
    n, d, rho = 100_000, 31, 0.6
    z = np.empty((n, d))
    z[:, 0] = rng.standard_normal(n)
    for t in range(1, d):
        z[:, t] = rho * z[:, t - 1] + np.sqrt(1 - rho**2) * rng.standard_normal(n)
    assert (z.mean(1).var() * d) == pytest.approx(ar1_mean_var_factor(rho, d), rel=0.03)


# ------------------------------------------------------------------------------- trend
def _trend_obs(seed=5, b_max=0.06, b_min=0.10, n_years=40, d=31):
    """Synthetic Julys with separate known linear trends (deg F / year) and AR(1) noise."""
    rng = np.random.default_rng(seed)
    years = np.arange(1980, 1980 + n_years)
    rows = []
    for y in years:
        z = np.empty(d)
        z[0] = rng.standard_normal()
        for t in range(1, d):
            z[t] = 0.6 * z[t - 1] + 0.8 * rng.standard_normal()
        tmax = 84 + b_max * (y - years[-1]) + 6 * z
        tmin = 64 + b_min * (y - years[-1]) + 5 * (0.7 * z + 0.71 * rng.standard_normal(d))
        for t in range(d):
            rows.append((dt.date(int(y), 7, 1) + dt.timedelta(days=t), tmax[t], tmin[t], 0.0))
    return pd.DataFrame(rows, columns=["date", "tmax_f", "tmin_f", "precip_in"]), (int(years[0]), int(years[-1]))


def test_separate_trends_recovered():
    from farmerjoe.model.climatology import fit_trend
    obs, yrs = _trend_obs()
    tr = fit_trend(obs, START, END, yrs)
    assert tr["tmax_f"]["beta_per_year"] == pytest.approx(0.06, abs=3 * tr["tmax_f"]["se_per_year"] + 0.01)
    assert tr["tmin_f"]["beta_per_year"] == pytest.approx(0.10, abs=3 * tr["tmin_f"]["se_per_year"] + 0.01)


def test_trend_not_counted_as_variability():
    """With a strong trend, detrending must remove it from the year-to-year spread (tau)."""
    from farmerjoe.model.climatology import fit_location
    obs, yrs = _trend_obs(b_max=0.4, b_min=0.4)        # 16 F rise over 40 years
    g = np.random.default_rng(1)
    obs["precip_in"] = np.where(g.random(len(obs)) < 0.3, g.gamma(0.8, 0.5, len(obs)) + 0.01, 0.0)
    rng = np.random.default_rng(0)
    on = fit_location(obs, START, END, yrs, rng, trend=True)
    off = fit_location(obs, START, END, yrs, rng, trend=False)
    assert on["tmax_f_tau"] < 0.5 * off["tmax_f_tau"]
    assert on["tmax_f_sd"] < off["tmax_f_sd"]
    assert on["tmax_f_mu"] == pytest.approx(84, abs=1.0)   # level at the last fit year
