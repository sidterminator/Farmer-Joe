"""Climatology (the prior), CLAUDE.md section 6.2.

Fits, per location, from historical days inside the season window (± buffer days):
  tmax, tmin ~ Normal(mu, sd)          one mu/sd for the whole window
  rho_tmax, rho_tmin                    lag-1 autocorrelation of standardized anomalies,
                                        using only consecutive-day pairs within one year
  corr_tmax_tmin                        same-day correlation of the two anomalies
  p_wet, p01, p11                       wet = precip >= 0.01 in; two-state Markov chain
  gamma_k, gamma_theta                  Gamma amounts on wet days, scipy gamma.fit(floc=0)
                                        on amounts >= 0.01 in. Note: amounts < 0.01 are
                                        recorded as trace/dry, so the data are really
                                        left-truncated. We checked truncation-aware MLE on
                                        ORD July: it fits the many 0.01-0.05" days better but
                                        overshoots the 99th percentile (2.9-3.3" vs 2.5"
                                        observed), while the plain fit matches the upper tail
                                        that drives season totals. Plain fit kept (per spec);
                                        it overestimates k slightly when k is small.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

WET_THRESHOLD_IN = 0.01


def window_mask(dates: pd.Series, start: dt.date, end: dt.date, buffer_days: int = 0) -> np.ndarray:
    """True for dates whose month-day falls in [start - buffer, end + buffer] of their own
    year (the season window projected onto every historical year)."""
    d = pd.to_datetime(dates)
    lo = pd.to_datetime([dt.date(y, start.month, start.day) for y in d.dt.year]) - pd.Timedelta(days=buffer_days)
    hi = pd.to_datetime([dt.date(y, end.month, end.day) for y in d.dt.year]) + pd.Timedelta(days=buffer_days)
    return ((d >= lo) & (d <= hi)).to_numpy()


def select_window(obs: pd.DataFrame, start: dt.date, end: dt.date, buffer_days: int,
                  years: tuple[int, int]) -> pd.DataFrame:
    """Rows in the (buffered) window and in years [y0, y1], with a `year` column."""
    d = pd.to_datetime(obs["date"])
    keep = window_mask(obs["date"], start, end, buffer_days) & d.dt.year.between(*years).to_numpy()
    out = obs.loc[keep].copy()
    out["year"] = pd.to_datetime(out["date"]).dt.year
    return out.sort_values("date").reset_index(drop=True)


def _lag1_pairs(df: pd.DataFrame, col: str) -> tuple[np.ndarray, np.ndarray]:
    """(x_t, x_{t+1}) pairs where both days are consecutive, in the same year, and non-NaN."""
    d = pd.to_datetime(df["date"]).to_numpy()
    x = df[col].to_numpy(dtype=float)
    yr = df["year"].to_numpy()
    ok = (np.diff(d) == np.timedelta64(1, "D")) & (yr[1:] == yr[:-1])
    a, b = x[:-1][ok], x[1:][ok]
    good = np.isfinite(a) & np.isfinite(b)
    return a[good], b[good]


def day_index(dates, start: dt.date) -> np.ndarray:
    """Days since the window's start month-day in each date's own year (0 = first day)."""
    d = pd.to_datetime(pd.Series(list(dates)))
    ref = pd.to_datetime(pd.Series([dt.date(y, start.month, start.day) for y in d.dt.year]))
    return (d - ref).dt.days.to_numpy()


MU_POLY_DEGREE = 2   # day-of-window mean: quadratic captures the seasonal ramp (e.g. Apr->May)


def fit_climatology(obs: pd.DataFrame, start: dt.date, end: dt.date,
                    years: tuple[int, int], buffer_days: int = 7) -> dict[str, Any]:
    """Fit climatology parameters for one location. `obs` has OBS_COLUMNS.

    Temperature mean varies by day of window (quadratic in day index, pooled over years), so
    a seasonal ramp is not mistaken for random variability; sd, rho and the tmax-tmin link are
    fit on anomalies from that curve. Rain occurrence/amount parameters are fit per calendar
    month of the window (rain_by_month) plus pooled values; persistence uses pooled stats.
    """
    w = select_window(obs, start, end, buffer_days, years)
    D = (end - start).days + 1
    w["t"] = day_index(w["date"], start)
    p: dict[str, Any] = {
        "fit_years": list(years), "buffer_days": buffer_days,
        "window_md": [start.strftime("%m-%d"), end.strftime("%m-%d")], "n_window_days": D,
        "n_days": int(len(w)), "n_years": int(w["year"].nunique()),
    }

    for v in ("tmax_f", "tmin_f"):
        m = w[v].notna().to_numpy()
        coef = np.polyfit(w["t"].to_numpy()[m], w[v].to_numpy()[m], MU_POLY_DEGREE)
        mu_t = np.polyval(coef, w["t"].to_numpy())
        resid = w[v].to_numpy() - mu_t
        p[f"{v}_mu_poly"] = [float(c) for c in coef]
        p[f"{v}_mu"] = float(np.polyval(coef, np.arange(D)).mean())   # window-average mean
        p[f"{v}_sd"] = float(np.nanstd(resid, ddof=1))
        w[f"{v}_z"] = resid / p[f"{v}_sd"]
        a, b = _lag1_pairs(w, f"{v}_z")
        p[f"{v}_rho"] = float(np.corrcoef(a, b)[0, 1])
    both = w[["tmax_f_z", "tmin_f_z"]].dropna()
    p["corr_tmax_tmin"] = float(np.corrcoef(both["tmax_f_z"], both["tmin_f_z"])[0, 1])

    pr = w["precip_in"]
    w["wet"] = np.where(pr.isna(), np.nan, (pr >= WET_THRESHOLD_IN).astype(float))
    p["p_wet"] = float(w["wet"].mean())
    a, b = _lag1_pairs(w, "wet")
    p["p01"] = float(b[a == 0].mean())   # P(wet today | dry yesterday)
    p["p11"] = float(b[a == 1].mean())   # P(wet today | wet yesterday)
    p["n_transitions"] = int(len(a))

    amt = pr[pr >= WET_THRESHOLD_IN].to_numpy()
    k, _, theta = stats.gamma.fit(amt, floc=0)
    p["gamma_k"], p["gamma_theta"] = float(k), float(theta)
    p["n_wet_days"] = int(len(amt))

    months = pd.to_datetime(w["date"]).dt.month
    p["rain_by_month"] = {}
    for mth in range(start.month, end.month + 1):
        sub = w[(months == mth).to_numpy()]
        am = sub["precip_in"][sub["precip_in"] >= WET_THRESHOLD_IN].to_numpy()
        if len(am) >= 30:
            km, _, thm = stats.gamma.fit(am, floc=0)
        else:  # too few wet days: fall back to pooled amounts
            km, thm = k, theta
        p["rain_by_month"][str(mth)] = {"p_wet": float(sub["wet"].mean()), "gamma_k": float(km),
                                        "gamma_theta": float(thm), "n_wet_days": int(len(am))}
    return p


def rain_day_arrays(p: dict[str, Any], d: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-day (p_wet, k, theta) arrays of length d from rain_by_month (pooled if absent)."""
    rbm = p.get("rain_by_month")
    if not rbm:
        return np.full(d, p["p_wet"]), np.full(d, p["gamma_k"]), np.full(d, p["gamma_theta"])
    m0, d0 = (int(x) for x in p["window_md"][0].split("-"))
    days = [dt.date(2001, m0, d0) + dt.timedelta(days=i) for i in range(d)]   # non-leap reference
    pick = [rbm.get(str(x.month), {"p_wet": p["p_wet"], "gamma_k": p["gamma_k"], "gamma_theta": p["gamma_theta"]})
            for x in days]
    return (np.array([q["p_wet"] for q in pick]), np.array([q["gamma_k"] for q in pick]),
            np.array([q["gamma_theta"] for q in pick]))


def historical_season_totals(obs: pd.DataFrame, start: dt.date, end: dt.date,
                             years: tuple[int, int]) -> pd.DataFrame:
    """Per-year season totals (no buffer) for years with a complete window.

    Columns: year, rain_total_in, hot_days_95, gdd, n_days.
    """
    from farmerjoe.outputs.aggregate import HOT_DAY_F, gdd_daily

    w = select_window(obs, start, end, 0, years)
    n_expected = (end - start).days + 1
    rows = []
    for y, g in w.groupby("year"):
        g = g.dropna(subset=["tmax_f", "tmin_f", "precip_in"])
        if len(g) < n_expected:
            continue  # incomplete season: skip rather than bias totals low
        rows.append({
            "year": int(y),
            "rain_total_in": float(g["precip_in"].sum()),
            "hot_days_95": int((g["tmax_f"] >= HOT_DAY_F).sum()),
            "gdd": float(gdd_daily(g["tmax_f"].to_numpy(), g["tmin_f"].to_numpy()).sum()),
            "n_days": len(g),
        })
    return pd.DataFrame(rows)


def save_params(params: dict[str, Any], path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(params, indent=2))


def load_params(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


# ------------------------------------------------------------- interannual variability
# A day-by-day model with one fixed mean underestimates year-to-year spread of season
# totals ("overdispersion"): real Julys have month-long anomalies (e.g. 2012 heat).
# We add a season-level component, fit by method of moments on the training years:
#   temperature: each season gets an offset delta ~ N(0, tau^2) (tmax/tmin correlated);
#                within-season sd shrinks to sqrt(sd^2 - tau^2) so the daily marginal
#                variance (and thus the mean of hot-day counts) is unchanged.
#   rain:        each season's wet-day amounts are scaled by M ~ LogNormal(-s^2/2, s^2)
#                (mean 1), with s chosen to match the variance of season totals.
# Excess variance is clipped at 0 (no component if the simulator already matches).

def ar1_mean_var_factor(rho: float, d: int) -> float:
    """Var(mean of d AR(1) values with unit variance) * d = 1 + 2*sum (1-k/d) rho^k."""
    k = np.arange(1, d)
    return float(1 + 2 * np.sum((1 - k / d) * rho**k))


def markov_gamma_total_moments(p01: float, p11: float, k: float, theta: float, d: int) -> tuple[float, float]:
    """Exact mean and variance of a d-day total from a stationary 2-state Markov chain
    with iid Gamma(k, theta) wet-day amounts (ignores the simulator's 0.01" floor,
    which changes the mean by < 0.1%)."""
    pi = p01 / (1 - p11 + p01)
    lam = p11 - p01
    m1, m2 = k * theta, k * (k + 1) * theta**2   # E[A], E[A^2]
    lags = np.arange(1, d)
    cov_sum = np.sum((d - lags) * lam**lags)
    mean = d * pi * m1
    var = d * (pi * m2 - (pi * m1) ** 2) + 2 * m1**2 * pi * (1 - pi) * cov_sum
    return float(mean), float(var)


def fit_interannual(obs: pd.DataFrame, params: dict[str, Any], start: dt.date, end: dt.date,
                    years: tuple[int, int]) -> dict[str, Any]:
    """Return params extended with season-level variability terms (see block comment)."""
    p = dict(params)
    d = (end - start).days + 1
    w = select_window(obs, start, end, 0, years)
    ym = w.groupby("year")[["tmax_f", "tmin_f"]].mean()
    for v in ("tmax_f", "tmin_f"):
        sd2, rho = p[f"{v}_sd"] ** 2, p[f"{v}_rho"]
        f = ar1_mean_var_factor(rho, d) / d
        tau2 = max(0.0, (ym[v].var(ddof=1) - sd2 * f) / (1 - f))
        tau2 = min(tau2, 0.5 * sd2)  # guard: never more than half the daily variance
        p[f"{v}_tau"] = float(np.sqrt(tau2))
        p[f"{v}_sd_within"] = float(np.sqrt(sd2 - tau2))
    p["tau_corr"] = float(np.clip(np.corrcoef(ym["tmax_f"], ym["tmin_f"])[0, 1], -0.99, 0.99))

    hist = historical_season_totals(obs, start, end, years)
    mean_s, var_s = markov_gamma_total_moments(p["p01"], p["p11"], p["gamma_k"], p["gamma_theta"], d)
    v_obs = float(hist["rain_total_in"].var(ddof=1))
    v_m = max(0.0, (v_obs - var_s) / (var_s + mean_s**2))
    p["rain_amount_logsd"] = float(np.sqrt(np.log1p(v_m)))
    p["interannual"] = True
    return p


# ------------------------------------------------------------------------ trend switch
def fit_trend(obs: pd.DataFrame, start: dt.date, end: dt.date, years: tuple[int, int]) -> dict[str, Any]:
    """Separate linear trends for tmax and tmin: OLS of each season mean on year.

    Returns {var: {beta_per_year, se, beta_f_per_decade, ref_year}} with ref_year = last fit
    year, so mu(year) = mu_ref + beta * (year - ref_year).
    """
    w = select_window(obs, start, end, 0, years)
    n_expected = (end - start).days + 1
    out: dict[str, Any] = {}
    for v in ("tmax_f", "tmin_f"):
        g = w.dropna(subset=[v]).groupby("year")[v].agg(["mean", "size"])
        g = g[g["size"] >= 0.9 * n_expected]
        x = g.index.to_numpy(dtype=float) - years[1]
        y = g["mean"].to_numpy()
        res = stats.linregress(x, y)
        out[v] = {"beta_per_year": float(res.slope), "se_per_year": float(res.stderr),
                  "beta_f_per_decade": round(float(res.slope) * 10, 3),
                  "se_f_per_decade": round(float(res.stderr) * 10, 3),
                  "ref_year": int(years[1]), "n_years": int(len(g))}
    return out


def detrend(obs: pd.DataFrame, trend: dict[str, Any]) -> pd.DataFrame:
    """Remove the fitted trend: x - beta * (year - ref_year), i.e. values at ref_year level."""
    out = obs.copy()
    yr = pd.to_datetime(out["date"]).dt.year.to_numpy()
    for v, t in trend.items():
        out[v] = out[v] - t["beta_per_year"] * (yr - t["ref_year"])
    return out


# --------------------------------------------------------------- rain latent persistence
def bvn_upper(h1: float, h2: float, r: float) -> float:
    """P(Z1 > h1, Z2 > h2) for standard bivariate normal with correlation r."""
    from scipy.stats import multivariate_normal
    return float(multivariate_normal(mean=[0, 0], cov=[[1, r], [r, 1]]).cdf([-h1, -h2]))


def solve_latent_corr(p1: float, p2: float, p_both: float) -> float:
    """Latent Gaussian correlation r such that P(wet1 & wet2) = p_both, where wet_i means
    Z_i > Phi^-1(1 - p_i) (dichotomized Gaussian). Clipped to the achievable range."""
    from scipy.optimize import brentq
    h1, h2 = stats.norm.ppf(1 - p1), stats.norm.ppf(1 - p2)
    f = lambda r: bvn_upper(h1, h2, r) - p_both
    lo, hi = -0.99, 0.995
    if f(lo) > 0:
        return lo
    if f(hi) < 0:
        return hi
    return float(brentq(f, lo, hi, xtol=1e-5))


def rain_latent_rho(p_wet: float, p11: float) -> float:
    """AR(1) coefficient of the rain latent so that simulated P(wet|wet yesterday) = p11."""
    return solve_latent_corr(p_wet, p_wet, p_wet * p11)


def wet_amount_persistence(obs: pd.DataFrame, start: dt.date, end: dt.date, years: tuple[int, int],
                           k: float, theta: float) -> float:
    """Lag-1 correlation of amount normal scores, Phi^-1(F_gamma(x)), over consecutive wet-day
    pairs within a season (clipped to [0, 0.9])."""
    w = select_window(obs, start, end, 0, years)
    w = w.assign(ns=np.where(w["precip_in"] >= WET_THRESHOLD_IN,
                             stats.norm.ppf(np.clip(stats.gamma.cdf(w["precip_in"], k, scale=theta), 1e-6, 1 - 1e-6)),
                             np.nan))
    a, b = _lag1_pairs(w, "ns")
    if len(a) < 30:
        return 0.0
    return float(np.clip(np.corrcoef(a, b)[0, 1], 0.0, 0.9))


def ar1_from(e: np.ndarray, rho: float) -> np.ndarray:
    """Stationary unit-variance AR(1) along axis 1 from standard-normal draws e (n, d)."""
    x = np.empty_like(e)
    x[:, 0] = e[:, 0]
    s = np.sqrt(1 - rho**2)
    for t in range(1, e.shape[1]):
        x[:, t] = rho * x[:, t - 1] + s * e[:, t]
    return x


def within_rhos(p: dict[str, Any], lam: float) -> tuple[float, float]:
    """Within-season AR coefficients for the rain occurrence and amount latents, given the
    season-level share lam: total lag-1 corr = (1 - lam) * rho_within + lam."""
    rw = max(0.0, (p["rain_rho"] - lam) / (1 - lam))
    aw = max(0.0, (p["rain_amount_rho_total"] - lam) / (1 - lam))
    return rw, aw


def rain_totals_single(p: dict[str, Any], d: int, lam: float, ez: np.ndarray, ew: np.ndarray,
                       g: np.ndarray, s_mult: float = 0.0) -> np.ndarray:
    """Season rain totals for one location under the latent model with season share lam,
    from given standard normals (common random numbers): ez, ew (n, d), g (n,)."""
    from farmerjoe.model.dependence import latent_to_rain
    rw, aw = within_rhos(p, lam)
    z = np.sqrt(1 - lam) * ar1_from(ez, rw) + np.sqrt(lam) * g[:, None]
    w = np.sqrt(1 - lam) * ar1_from(ew, aw) + np.sqrt(lam) * g[:, None]
    pw, k, th = rain_day_arrays(p, d)
    mult = np.exp(s_mult * g - s_mult**2 / 2)[:, None] if s_mult > 0 else None
    return latent_to_rain(z, pw, k, th, mult, w).sum(axis=1)


def fit_location(obs: pd.DataFrame, start: dt.date, end: dt.date, years: tuple[int, int],
                 rng: np.random.Generator, buffer_days: int = 0, trend: bool = False,
                 interannual: bool = True) -> dict[str, Any]:
    """Full Phase 2 climatology fit for one location.

    trend on: fit separate tmax/tmin trends, then fit everything else on detrended values
    (mu = level at the last fit year). Rain gets the latent AR(1) coefficient (rain_rho).
    Interannual: temperature offsets (method of moments) and a rain-amount multiplier sized
    against the latent rain model's own season-total variance.
    """
    tr = fit_trend(obs, start, end, years) if trend else None
    o = detrend(obs, tr) if tr else obs
    p = fit_climatology(o, start, end, years, buffer_days)
    p["trend"] = tr
    p["rain_rho"] = rain_latent_rho(p["p_wet"], p["p11"])
    if interannual:
        p = fit_interannual(o, p, start, end, years)
        # Rain spread. Wet and dry summers differ in how OFTEN it rains, not just how much,
        # and the signal is regional. A season-level latent g (share lam of the rain latent's
        # variance, shared by occurrence and amounts) carries that; lam is chosen so the
        # variance of season totals matches history. Amount persistence is measured from data.
        # If lam at its maximum (= the observed lag-1 latent corr) is still too narrow, a
        # mean-1 multiplier driven by the same g adds the rest.
        d = (end - start).days + 1
        p["rain_amount_rho_total"] = wet_amount_persistence(o, start, end, years, p["gamma_k"], p["gamma_theta"])
        v_obs = float(historical_season_totals(o, start, end, years)["rain_total_in"].var(ddof=1))
        n = 12_000
        ez, ew, g = rng.standard_normal((n, d)), rng.standard_normal((n, d)), rng.standard_normal(n)
        lam_max = float(min(p["rain_rho"], 0.8))
        grid = np.linspace(0.0, lam_max, 9)
        var = np.maximum.accumulate(np.array([rain_totals_single(p, d, l, ez, ew, g).var(ddof=1) for l in grid]))
        s_mult = 0.0
        if var[0] >= v_obs:
            lam = 0.0
        elif var[-1] >= v_obs:
            lam = float(np.interp(v_obs, var, grid))
        else:
            lam = lam_max
            for s_try in np.linspace(0.05, 1.0, 20):
                s_mult = float(s_try)
                if rain_totals_single(p, d, lam, ez, ew, g, s_mult).var(ddof=1) >= v_obs:
                    break
        p["rain_year_share"] = lam
        p["rain_rho_within"], p["rain_amount_rho"] = within_rhos(p, lam)
        p["rain_amount_logsd"] = s_mult
        p["rain_total_var_model_vs_obs"] = [round(float(rain_totals_single(p, d, lam, ez, ew, g, s_mult).var(ddof=1)), 4),
                                            round(v_obs, 4)]
    return p


def mu_curve(p: dict[str, Any], var: str, year: int, d: int) -> np.ndarray:
    """Day-of-window mean (length d) for a target season year, trend applied if fitted."""
    coef = p.get(f"{var}_mu_poly")
    base = np.polyval(coef, np.arange(d)) if coef else np.full(d, p[f"{var}_mu"])
    tr = p.get("trend")
    if tr:
        base = base + tr[var]["beta_per_year"] * (year - tr[var]["ref_year"])
    return base


def mu_at(p: dict[str, Any], var: str, year: int) -> float:
    """Location mean of tmax_f/tmin_f for a target season year (applies the trend if fitted)."""
    mu = p[f"{var}_mu"]
    tr = p.get("trend")
    if tr:
        mu += tr[var]["beta_per_year"] * (year - tr[var]["ref_year"])
    return float(mu)
