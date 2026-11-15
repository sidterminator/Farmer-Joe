"""Hedge model v1 end to end (HEDGE_MODEL.md §5-7): used by `run.py --mode hedge` and server.py."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from farmerjoe.hedge.menu import build_menu, sides
from farmerjoe.hedge.revenue import natural_hedge, simulate_revenue
from farmerjoe.hedge.search import decide, evaluate, greedy_search, max_entry_price
from farmerjoe.hedge.settings import load_hedge_settings


def run_hedge(run_dir: str | Path, overrides: dict[str, Any] | None = None, seed: int | None = None,
              write: bool = True) -> dict[str, Any]:
    """Revenue, menu, greedy hedge, entry prices and decision for a weather run folder."""
    run_dir = Path(run_dir)
    meta = json.loads((run_dir / "run_meta.json").read_text())
    season = pd.read_parquet(run_dir / "scenarios_season.parquet").sort_values("scenario_id").reset_index(drop=True)
    s = load_hedge_settings(meta["crop"], overrides)
    rng = np.random.default_rng(meta["seed"] if seed is None else seed)   # the one rng for this run
    rng_rev, rng_nh = rng.spawn(2)
    rev = simulate_revenue(season, s, rng_rev)
    nh = natural_hedge(rev, s, rng_nh)
    contracts, yes = build_menu(season, rev, meta["stations"], s)
    tab, pay = sides(contracts, yes)
    contract_of = tab["contract_id"].map({c: i for i, c in enumerate(contracts.contract_id)}).to_numpy()
    n = len(rev)
    train, test = np.arange(n // 2), np.arange(n // 2, n)
    revenue = rev["revenue_usd"].to_numpy()
    asks = tab["ask"].to_numpy()
    w, a, budget = s["risk_weight"], s["cvar_alpha"], s["budget_usd"]
    g = greedy_search(revenue, pay, asks, contract_of, budget, w, train, int(s["max_legs"]), a,
                      int(s["size_steps"]), int(s["lot"]))
    legs = g["legs"]
    ev = evaluate(revenue, pay, asks, legs, test, a)
    max_he = (meta.get("hedge_diagnostics", {}).get("rain_total_in") or {}).get("max_hedge_effectiveness")
    decision, reason = decide(ev, nh["natural_hedge_pct"], max_he, s["rule"])
    if decision == "partial":
        legs = [(j, math.floor(k / 2 / s["lot"]) * s["lot"]) for j, k in legs]
        legs = [(j, k) for j, k in legs if k > 0]
        ev = evaluate(revenue, pay, asks, legs, test, a)
    best_available = None
    if decision == "none" and legs:
        # Recommend nothing, but report the single best contract the search found.
        j, cnt = legs[0]
        best_available = {"key": tab.key[j], "contract_id": tab.contract_id[j], "side": tab.side[j],
                          "contracts": int(cnt), "dollars": float(cnt * asks[j])}
        legs = []
    rows = []
    for k, (j, cnt) in enumerate(legs):
        t = tab.iloc[j]
        mx = max_entry_price(revenue, pay, asks, legs, k, budget, w, train, a, int(s["size_steps"]), int(s["lot"]),
                             int(s["min_leg"]))
        rows.append({"contract_id": t.contract_id, "key": t.key, "family": t.family, "station_or_crop": t.location,
                     "side": t.side, "condition": f"{t.variable} {t.comparator} {t.threshold:g}",
                     "p_model": float(t.p_yes), "fair_value": float(t.fair_value), "ask": float(t.ask),
                     "max_entry_price": float(mx), "limit_price": math.floor(min(t.ask, mx) * 100) / 100,
                     "contracts": int(cnt), "dollars": float(cnt * t.ask), "payout_if_hit": float(cnt)})
    legs_df = pd.DataFrame(rows, columns=["contract_id", "key", "family", "station_or_crop", "side", "condition",
                                          "p_model", "fair_value", "ask", "max_entry_price", "limit_price",
                                          "contracts", "dollars", "payout_if_hit"])
    hedged = revenue.copy()
    for j, cnt in legs:
        hedged = hedged + cnt * (pay[:, j] - asks[j])
    rec = {"decision": decision, "reason": reason, "eval_half": ev, "best_available": best_available,
           "natural_hedge": nh, "hypothetical": True, "placeholders": True,
           "legs": legs_df.to_dict("records"), "settings": s, "weather_run": meta["run_id"],
           "note": "Educational tool, not financial advice. Contracts are hypothetical; "
                   "yield and price settings are placeholders."}
    out = {"meta": meta, "settings": s, "rev": rev, "hedged": hedged, "nh": nh, "contracts": contracts,
           "yes": yes, "sides": tab, "legs": legs_df, "rec": rec, "eval": ev, "train": train, "test": test}
    if write:
        d = run_dir / "hedge"
        (d / "plots").mkdir(parents=True, exist_ok=True)
        rv = rev.assign(hedged_pl_usd=hedged)[["scenario_id", "farm_yield_bu_ac", "region_dev", "price_usd_bu",
                                               "revenue_usd", "hedged_pl_usd"]]
        rv.to_parquet(d / "revenue_scenarios.parquet", index=False)
        (d / "recommendation.json").write_text(json.dumps(rec, indent=2, default=float))
        legs_df.drop(columns="key").to_csv(d / "legs.csv", index=False)
        from farmerjoe.validate.plots import plot_revenue_before_after
        who = meta["farm"].get("name") or f"({meta['farm']['lat']}, {meta['farm']['lon']})"
        plot_revenue_before_after(revenue[test], hedged[test], d / "plots" / "revenue_before_after.png",
                                  f"{who}, {meta['crop']}: {decision.upper()} — revenue unhedged vs hedged (evaluation half)")
        out["dir"] = d
    return out
