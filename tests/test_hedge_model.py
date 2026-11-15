"""Hedge model v1 tests (HEDGE_MODEL.md §9; H0-H1 parts)."""
import numpy as np
import pandas as pd
import pytest

from farmerjoe.hedge.revenue import natural_hedge, simulate_revenue
from farmerjoe.hedge.search import cvar, evaluate, single_leg_search, size_grid
from farmerjoe.hedge.settings import load_hedge_settings


def test_toy_two_state_equalizes_revenue():
    """Good year 100k, bad year 40k, 50/50; contract pays $1 in the bad year at fair ask 0.5.
    The best hedge buys 60,000: 40k + 60k*(1-0.5) = 100k - 60k*0.5 = 70k in both states."""
    n = 2000
    bad = np.arange(n) % 2 == 0
    revenue = np.where(bad, 40_000.0, 100_000.0)
    pay = bad.astype(float)[:, None]
    for w in (1.0, 0.7):
        best = single_leg_search(revenue, pay, np.array([0.5]), 30_000, w, np.arange(n), steps=40, lot=100)
        assert best["n"] == pytest.approx(60_000)
        ev = evaluate(revenue, pay, np.array([0.5]), [(0, best["n"])], np.arange(n))
        assert ev["after"]["sd"] == pytest.approx(0, abs=1e-6) and ev["cost"] == pytest.approx(0, abs=1e-6)


def test_budget_respected_and_grid_lots():
    g = size_grid(0.37, 15_000, 40, 100)
    assert (g * 0.37 <= 15_000 + 1e-9).all() and (g % 100 == 0).all() and g[0] == 0
    rng = np.random.default_rng(0)
    revenue = rng.normal(500_000, 80_000, 4000)
    pay = (rng.random((4000, 5)) < 0.3).astype(float)
    best = single_leg_search(revenue, pay, np.full(5, 0.33), 15_000, 0.7, np.arange(2000))
    assert best["j"] is None or best["n"] * 0.33 <= 15_000


def test_cvar():
    x = np.arange(100, dtype=float)
    assert cvar(x, 0.05) == pytest.approx(2.0)   # mean of 0..4


def _season(n=20_000, link=0.9, seed=1):
    """Farm and two index regions with correlated rain and heat (a 'core' farm)."""
    rng = np.random.default_rng(seed)
    common_r, common_h = rng.standard_normal(n), rng.standard_normal(n)
    def loc(c):
        r = np.clip(4 + 1.8 * (link * common_r + np.sqrt(1 - link**2) * rng.standard_normal(n)), 0, None)
        h = np.clip(np.round(1 + 1.5 * (link * common_h + np.sqrt(1 - link**2) * rng.standard_normal(n))), 0, None)
        return {f"rain_total_in_{c}": r, f"hot_days_95_{c}": h, f"gdd_{c}": np.zeros(n)}
    d = {"scenario_id": np.arange(n)}
    for c in ("farm", "IDX_A", "IDX_B"):
        d.update(loc(c))
    return pd.DataFrame(d)


def test_natural_hedge_sign_and_zero():
    s = load_hedge_settings("corn")
    season = _season()
    rev = simulate_revenue(season, s, np.random.default_rng(2), rho=-0.5)
    assert natural_hedge(rev, s, np.random.default_rng(3))["natural_hedge_pct"] > 0.02
    rev0 = simulate_revenue(season, s, np.random.default_rng(2), rho=0.0)
    assert abs(natural_hedge(rev0, s, np.random.default_rng(3))["natural_hedge_pct"]) < 0.02


def test_same_seed_same_result():
    s = load_hedge_settings("corn")
    season = _season(4000)
    a = simulate_revenue(season, s, np.random.default_rng(7))
    b = simulate_revenue(season, s, np.random.default_rng(7))
    pd.testing.assert_frame_equal(a, b)
    assert (a.price_usd_bu > 0).all() and a.price_usd_bu.mean() == pytest.approx(4.5, rel=0.02)


def test_greedy_respects_budget_and_sides():
    from farmerjoe.hedge.search import greedy_search
    rng = np.random.default_rng(4)
    n = 6000
    bad = rng.random(n) < 0.3
    revenue = np.where(bad, 300_000.0, 450_000.0) + rng.normal(0, 20_000, n)
    yes = np.column_stack([bad, rng.random(n) < 0.5, bad & (rng.random(n) < 0.7)]).astype(float)
    pay = np.concatenate([yes, 1 - yes], axis=1)
    p = yes.mean(0)
    asks = np.concatenate([p + 0.03, 1 - p + 0.03])
    contract_of = np.array([0, 1, 2, 0, 1, 2])
    g = greedy_search(revenue, pay, asks, contract_of, 15_000, 0.7, np.arange(n // 2), max_legs=3)
    assert sum(k * asks[j] for j, k in g["legs"]) <= 15_000 + 1e-6
    assert len({contract_of[j] for j, _ in g["legs"]}) == len(g["legs"])     # never YES+NO of one contract
    assert g["legs"] and contract_of[g["legs"][0][0]] in (0, 2)               # buys the bad-year payer


def test_stations_js_is_the_market_list():
    from farmerjoe.config import load_config
    cfg = load_config(overrides={"farm": "champaign_corn"})
    assert len(cfg.market_stations) == 38
    assert cfg.market_stations["CHI"]["series"] == "KXRAINCHIM" and cfg.market_stations["CHI"]["markets"] == ["rain"]
    assert cfg.market_stations["DFW"]["markets"] == ["tmax"]
    assert not any(m["verified_market"] for m in cfg.market_stations.values())
