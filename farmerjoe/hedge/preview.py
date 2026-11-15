"""H0/H1 review: revenue + natural hedge + contract menu + best single leg for a weather run.

    .venv/bin/python -m farmerjoe.hedge.preview [--run outputs/<run_id>] [--budget 15000] [--risk-weight 0.7]

(`--mode hedge` with multi-leg search, entry prices and the decision rule arrives in H2.)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from farmerjoe.hedge.menu import build_menu, sides
from farmerjoe.hedge.revenue import natural_hedge, simulate_revenue
from farmerjoe.hedge.search import evaluate, single_leg_search
from farmerjoe.hedge.settings import load_hedge_settings
from farmerjoe.validate.plots import plot_revenue_before_after


def run_preview(run_dir: Path, overrides: dict, seed: int | None = None) -> dict:
    meta = json.loads((run_dir / "run_meta.json").read_text())
    season = pd.read_parquet(run_dir / "scenarios_season.parquet").sort_values("scenario_id").reset_index(drop=True)
    s = load_hedge_settings(meta["crop"], overrides)
    rng = np.random.default_rng(meta["seed"] if seed is None else seed)   # the one rng for this run
    rng_rev, rng_nh = rng.spawn(2)
    rev = simulate_revenue(season, s, rng_rev)
    nh = natural_hedge(rev, s, rng_nh)
    contracts, yes = build_menu(season, rev, meta["stations"], s)
    tab, pay = sides(contracts, yes)
    n = len(rev)
    train, test = np.arange(n // 2), np.arange(n // 2, n)
    revenue = rev["revenue_usd"].to_numpy()
    asks = tab["ask"].to_numpy()
    best = single_leg_search(revenue, pay, asks, s["budget_usd"], s["risk_weight"], train,
                             s["cvar_alpha"], s["size_steps"], s["lot"])
    legs = [] if best["j"] is None else [(best["j"], best["n"])]
    ev = evaluate(revenue, pay, asks, legs, test, s["cvar_alpha"])

    # per-family best single leg (what each contract type alone could do)
    fam = []
    for f in ("rain", "heat", "price"):
        cols = np.flatnonzero((tab["family"] == f).to_numpy())
        if len(cols) == 0:
            continue
        b = single_leg_search(revenue, pay[:, cols], asks[cols], s["budget_usd"], s["risk_weight"], train,
                              s["cvar_alpha"], s["size_steps"], s["lot"])
        lg = [] if b["j"] is None else [(cols[b["j"]], b["n"])]
        e = evaluate(revenue, pay, asks, lg, test, s["cvar_alpha"])
        fam.append(dict(family=f, contract=tab.contract_id[lg[0][0]] + " " + tab.side[lg[0][0]] if lg else "(none)",
                        contracts=lg[0][1] if lg else 0, dollars=lg[0][1] * asks[lg[0][0]] if lg else 0.0,
                        delta_cvar5=e["delta_cvar5"], cost=e["cost"]))

    out = run_dir / "hedge"
    (out / "plots").mkdir(parents=True, exist_ok=True)
    hedged = revenue.copy()
    for j, k in legs:
        hedged = hedged + k * (pay[:, j] - asks[j])
    who = meta["farm"].get("name") or f"({meta['farm']['lat']}, {meta['farm']['lon']})"
    label = (f"best single leg: {int(legs[0][1]):,} × {tab.contract_id[legs[0][0]]} {tab.side[legs[0][0]]}"
             if legs else "no leg improves the score")
    plot_revenue_before_after(revenue[test], hedged[test], out / "plots" / "revenue_before_after_H1.png",
                              f"{who}, {meta['crop']}: revenue, unhedged vs {label} (evaluation half)")
    return {"meta": meta, "settings": s, "rev": rev, "nh": nh, "contracts": contracts, "sides": tab,
            "best": best, "legs": legs, "eval": ev, "families": pd.DataFrame(fam), "out": out}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", help="weather run folder (default: outputs/latest_run.txt)")
    ap.add_argument("--budget", type=float, dest="budget_usd")
    ap.add_argument("--risk-weight", type=float, dest="risk_weight")
    ap.add_argument("--acres", type=float)
    a = ap.parse_args(argv)
    run_dir = Path(a.run) if a.run else Path(Path("outputs/latest_run.txt").read_text().strip())
    res = run_preview(run_dir, {k: v for k, v in vars(a).items() if k != "run"})
    m, s, rev, nh, ev = res["meta"], res["settings"], res["rev"], res["nh"], res["eval"]
    pd.set_option("display.width", 160)
    print(f"\n=== {m['farm'].get('name') or m['farm']} — {m['crop']} {m['window']['start']}..{m['window']['end']}  "
          f"(placeholder economics: {s['acres']:.0f} ac × {s['aph_yield_bu_ac']} bu/ac @ ${s['futures_price_usd_bu']})")
    r = rev["revenue_usd"]
    print(f"H0 revenue: mean ${r.mean():,.0f}  sd ${r.std():,.0f}  p5 ${np.percentile(r, 5):,.0f}   "
          f"yield mean {rev.farm_yield_bu_ac.mean():.1f} bu/ac   price mean ${rev.price_usd_bu.mean():.2f}")
    print(f"   natural hedge: {nh['natural_hedge_pct']:.1%} of revenue sd removed "
          f"(corr yield–price {nh['corr_yield_price']:.2f})")
    c = res["contracts"]
    print(f"H1 menu: {len(c)} contracts ({', '.join(f'{k} {v}' for k, v in c.family.value_counts().items())}), "
          f"{len(res['sides'])} tradable sides; all hypothetical, ask = p + {s['ask_markup']}")
    if res["legs"]:
        j, n = res["legs"][0]
        t = res["sides"].iloc[j]
        print(f"   best single leg (chosen on scenarios 0–4,999): {int(n):,} × {t.contract_id} {t.side} "
              f"@ ask {t.ask:.2f} (fair {t.fair_value:.2f}) = ${n * t.ask:,.0f}")
    else:
        print("   best single leg: none improves the score")
    b, a2 = ev["before"], ev["after"]
    print(f"   eval half (5,000–9,999): CVaR5 ${b['cvar5']:,.0f} → ${a2['cvar5']:,.0f} (Δ ${ev['delta_cvar5']:+,.0f}, "
          f"{ev['delta_cvar5'] / ev['shortfall']:.1%} of shortfall); cost ${ev['cost']:,.0f} "
          f"({ev['cost'] / b['mean']:.2%} of mean revenue)")
    print("   best single leg by family (eval half):")
    print(res["families"].round(0).to_string(index=False))
    print(f"   plot: {(res['out'] / 'plots' / 'revenue_before_after_H1.png').resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
