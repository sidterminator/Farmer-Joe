"""Simulator tests: reproducibility, shapes, p_se, p_wet."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from farmerjoe.fetch.history import parse_ncei_records
from farmerjoe.model.simulate import simulate_climatology
from farmerjoe.outputs.contracts import candidate_contracts, contract_probs
from farmerjoe.outputs.write import write_run
from farmerjoe.outputs import schema

P = dict(tmax_f_mu=84.25, tmax_f_sd=6.63, tmax_f_rho=0.62, tmin_f_mu=65.0, tmin_f_sd=6.12,
         tmin_f_rho=0.70, corr_tmax_tmin=0.71, p_wet=0.311, p01=0.264, p11=0.438,
         gamma_k=0.6, gamma_theta=0.68)
P_IA = dict(P, interannual=True, tmax_f_tau=2.28, tmax_f_sd_within=6.22, tmin_f_tau=1.81,
            tmin_f_sd_within=5.85, tau_corr=0.92, rain_amount_logsd=0.24)


@pytest.mark.parametrize("params", [P, P_IA])
def test_reproducible_and_shapes(params):
    a = simulate_climatology([params, params], 500, 31, np.random.default_rng(42))
    b = simulate_climatology([params, params], 500, 31, np.random.default_rng(42))
    c = simulate_climatology([params, params], 500, 31, np.random.default_rng(43))
    for k in ("tmax_f", "tmin_f", "precip_in"):
        assert a[k].shape == (500, 31, 2)
        np.testing.assert_array_equal(a[k], b[k])
    assert not np.array_equal(a["tmax_f"], c["tmax_f"])
    assert (a["tmin_f"] <= a["tmax_f"]).all() and (a["precip_in"] >= 0).all()


@pytest.mark.parametrize("params", [P, P_IA])
def test_marginals_match_inputs(params):
    a = simulate_climatology([params], 20_000, 31, np.random.default_rng(0))
    wet = a["precip_in"][..., 0] >= 0.01
    pi = params["p01"] / (1 - params["p11"] + params["p01"])
    assert wet.mean() == pytest.approx(pi, abs=0.01)
    assert wet.mean() == pytest.approx(params["p_wet"], abs=0.02)
    # simulated transitions
    prev, cur = wet[:, :-1], wet[:, 1:]
    assert cur[prev].mean() == pytest.approx(params["p11"], abs=0.01)
    assert cur[~prev].mean() == pytest.approx(params["p01"], abs=0.01)
    tx = a["tmax_f"][..., 0]
    assert tx.mean() == pytest.approx(params["tmax_f_mu"], abs=0.15)
    assert tx.std() == pytest.approx(params["tmax_f_sd"], rel=0.03)
    z = (tx - tx.mean()) / tx.std()
    within = np.corrcoef((tx - tx.mean(1, keepdims=True))[:, :-1].ravel(),
                         (tx - tx.mean(1, keepdims=True))[:, 1:].ravel())[0, 1]
    assert np.isfinite(within)
    if not params.get("interannual"):
        assert np.corrcoef(z[:, :-1].ravel(), z[:, 1:].ravel())[0, 1] == pytest.approx(params["tmax_f_rho"], abs=0.02)


def test_interannual_widens_season_spread():
    a = simulate_climatology([P], 20_000, 31, np.random.default_rng(1))
    b = simulate_climatology([P_IA], 20_000, 31, np.random.default_rng(1))
    assert b["precip_in"].sum(1).std() > a["precip_in"].sum(1).std() * 1.05
    assert b["tmax_f"].mean(1).std() > a["tmax_f"].mean(1).std() * 1.2
    # daily marginal sd is preserved
    assert b["tmax_f"].std() == pytest.approx(a["tmax_f"].std(), rel=0.03)


def test_p_se_formula(tmp_path):
    n = 400
    dates = [dt.date(2027, 7, 1) + dt.timedelta(days=i) for i in range(31)]
    arrays = simulate_climatology([P], n, 31, np.random.default_rng(5))
    meta = {"run_id": "t", "created_at": "x", "forecast_issue_time": None, "N": n, "seed": 5,
            "window": {"start": "2027-07-01", "end": "2027-07-31"}, "farm": {"lat": 40.1, "lon": -88.2},
            "stations": ["ORD"], "model_version": "t", "phase": 1, "calibration_scores": None}
    _, contracts = write_run(tmp_path, arrays, dates, ["ORD"], ["ORD"], dates[:3], {}, meta)
    p = contracts.p_model.to_numpy()
    np.testing.assert_allclose(contracts.p_se, np.sqrt(p * (1 - p) / n))
    assert schema.validate_run_dir(tmp_path)["N"] == n


def test_parse_ncei_records():
    recs = [
        {"DATE": "2024-07-01", "TMAX": "  75", "TMIN": "54", "PRCP": "0.00",
         "TMAX_ATTRIBUTES": ",,W,2400", "TMIN_ATTRIBUTES": ",,W,2400", "PRCP_ATTRIBUTES": "T,,W,2400"},
        {"DATE": "2024-07-02", "TMAX": "85", "TMIN": "67", "PRCP": "0.31",
         "TMAX_ATTRIBUTES": ",X,W,2400", "PRCP_ATTRIBUTES": ",,W,2400"},       # QC-flagged TMAX
        {"DATE": "2024-07-03", "TMIN": "73", "PRCP": "1.20"},                  # TMAX missing
    ]
    df = parse_ncei_records(recs)
    assert list(df.columns) == ["date", "tmax_f", "tmin_f", "precip_in"]
    assert df.tmax_f.iloc[0] == 75 and df.precip_in.iloc[0] == 0.0     # trace -> 0 (dry)
    assert np.isnan(df.tmax_f.iloc[1]) and df.precip_in.iloc[1] == 0.31
    assert np.isnan(df.tmax_f.iloc[2]) and df.tmin_f.iloc[2] == 73


# ------------------------------------------------------------------------- joint model
def _joint_params():
    from farmerjoe.model.climatology import rain_latent_rho
    base = dict(P_IA)
    base["trend"] = None
    base["rain_rho"] = rain_latent_rho(base["p_wet"], base["p11"])
    return {"farm": dict(base), "ORD": dict(base, tmax_f_mu=83.0), "IDX_IA": dict(base, p_wet=0.4,
            rain_rho=rain_latent_rho(0.4, 0.55))}


def _dep(r_t=0.8, r_r=0.6):
    L = 3
    R_t = np.full((2 * L, 2 * L), r_t * 0.8)
    np.fill_diagonal(R_t, 1.0)
    R_r = np.full((L, L), r_r)
    np.fill_diagonal(R_r, 1.0)
    return {"locations": ["farm", "ORD", "IDX_IA"], "R_within": R_t.tolist(), "R_year": R_t.tolist(),
            "R_rain": R_r.tolist(), "R_mult": np.eye(L).tolist()}


def test_joint_reproducible_shapes_and_marginals():
    from farmerjoe.model.dependence import simulate_joint
    P, dep = _joint_params(), _dep()
    a = simulate_joint(P, dep, 4000, 31, 2027, np.random.default_rng(1))
    b = simulate_joint(P, dep, 4000, 31, 2027, np.random.default_rng(1))
    for k in ("tmax_f", "tmin_f", "precip_in"):
        assert a[k].shape == (4000, 31, 3)
        np.testing.assert_array_equal(a[k], b[k])
    wet = a["precip_in"] >= 0.01
    assert wet[..., 0].mean() == pytest.approx(P["farm"]["p_wet"], abs=0.015)
    assert wet[..., 2].mean() == pytest.approx(0.4, abs=0.015)
    prev, cur = wet[:, :-1, 2], wet[:, 1:, 2]
    assert cur[prev].mean() == pytest.approx(0.55, abs=0.02)        # latent rho matches p11
    assert a["tmax_f"][..., 1].mean() == pytest.approx(83.0, abs=0.3)
    assert (a["tmin_f"] <= a["tmax_f"]).all()


def test_joint_cross_location_dependence():
    from farmerjoe.model.dependence import simulate_joint
    P = _joint_params()
    hi = simulate_joint(P, _dep(0.9, 0.8), 4000, 31, 2027, np.random.default_rng(2))
    lo = simulate_joint(P, _dep(0.1, 0.05), 4000, 31, 2027, np.random.default_rng(2))
    c = lambda x: np.corrcoef(x[..., 0].sum(1), x[..., 1].sum(1))[0, 1]
    assert c(hi["precip_in"]) > c(lo["precip_in"]) + 0.3
    assert c(hi["tmax_f"]) > c(lo["tmax_f"]) + 0.3


def test_trend_shifts_mean_by_target_year():
    from farmerjoe.model.dependence import simulate_joint
    P = _joint_params()
    for p in P.values():
        p["trend"] = {"tmax_f": {"beta_per_year": 0.1, "ref_year": 2019},
                      "tmin_f": {"beta_per_year": 0.0, "ref_year": 2019}}
    a = simulate_joint(P, _dep(), 4000, 31, 2029, np.random.default_rng(3))
    assert a["tmax_f"][..., 0].mean() == pytest.approx(P["farm"]["tmax_f_mu"] + 1.0, abs=0.25)


def test_index_series_is_mean_of_points(tmp_path, monkeypatch):
    from farmerjoe.fetch import history
    days = pd.date_range("2000-07-01", "2000-07-31").date
    def fake(lat, lon, years, months, cache_dir, budget=None):
        return pd.DataFrame({"date": days, "tmax_f": lat, "tmin_f": lat - 20, "precip_in": abs(lon) / 100})
    monkeypatch.setattr(history, "fetch_openmeteo_season", fake)
    idx = history.fetch_index_history([[40, -90], [42, -94]], (2000, 2000), (7, 7), tmp_path)
    assert (idx.tmax_f == 41).all() and np.allclose(idx.precip_in, 0.92)


def test_monthly_contracts_from_daily(tmp_path):
    import datetime as dt
    dates = [dt.date(2027, 4, 1) + dt.timedelta(days=i) for i in range(61)]
    arrays = simulate_climatology([P], 300, 61, np.random.default_rng(9))
    meta = {"run_id": "t", "created_at": "x", "forecast_issue_time": None, "N": 300, "seed": 9,
            "window": {"start": "2027-04-01", "end": "2027-05-31"}, "farm": {"lat": 38.8, "lon": -97.6},
            "stations": ["DEN"], "model_version": "t", "phase": 2, "calibration_scores": None}
    _, contracts = write_run(tmp_path, arrays, dates, ["DEN"], {"DEN": ["rain"]}, [], {}, meta)
    assert set(contracts.start.astype(str)) == {"2027-04-01", "2027-05-01"}
    apr = arrays["precip_in"][:, :30, 0].astype(np.float32).sum(1)
    c = contracts[(contracts.start.astype(str) == "2027-04-01") & (contracts.comparator == "lt")
                  & (contracts.threshold == 2.0)]
    assert c.p_model.iloc[0] == pytest.approx((apr < 2.0).mean(), abs=1e-9)
