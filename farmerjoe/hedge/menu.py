"""Contract menu + synthetic prices (HEDGE_MODEL.md §4). Season-level contracts only."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

RAIN_LT_PCTS = (10, 20, 30, 40)
RAIN_GE_PCTS = (70, 80, 90)
HEAT_PCTS = (60, 75, 90)
PRICE_MULTS = (0.80, 0.90, 1.10, 1.20)


def _fmt(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".")


def build_menu(season: pd.DataFrame, rev: pd.DataFrame, stations: list[str],
               s: dict[str, Any]) -> tuple[pd.DataFrame, np.ndarray]:
    """Return (contracts, yes_payoffs). contracts has one row per contract with p_yes and
    YES/NO asks; yes_payoffs is (N, K) of 0/1 (NO payoff = 1 - YES). Rows align on scenario_id."""
    season = season.sort_values("scenario_id").reset_index(drop=True)
    rows, cols = [], []

    def add(cid, family, where, variable, cmp, thr, x, key):
        pay = (x < thr) if cmp == "lt" else (x >= thr)
        rows.append(dict(contract_id=cid, family=family, location=where, variable=variable,
                         comparator=cmp, threshold=float(thr), key=key))
        cols.append(pay.astype(np.int8))

    for st in stations:
        r = season[f"rain_total_in_{st}"].to_numpy(float)
        for q in RAIN_LT_PCTS:
            t = round(float(np.percentile(r, q)), 2)
            add(f"{st}_RAIN_SEASON_LT_{_fmt(t)}", "rain", st, "rain_total_in", "lt", t, r, f"{st.lower()}_rain_lt_p{q}")
        for q in RAIN_GE_PCTS:
            t = round(float(np.percentile(r, q)), 2)
            add(f"{st}_RAIN_SEASON_GE_{_fmt(t)}", "rain", st, "rain_total_in", "ge", t, r, f"{st.lower()}_rain_ge_p{q}")
        h = season[f"hot_days_95_{st}"].to_numpy(float)
        for k in sorted({max(1, int(np.ceil(np.percentile(h, q)))) for q in HEAT_PCTS}):
            add(f"{st}_HOT95_SEASON_GE_{k}", "heat", st, "hot_days_95", "ge", k, h, f"{st.lower()}_heat_ge_{k}")
    price = rev.sort_values("scenario_id")["price_usd_bu"].to_numpy(float)
    F = s["futures_price_usd_bu"]
    for m in PRICE_MULTS:
        K = round(F * m, 2)
        for cmp in ("lt", "ge"):
            add(f"{s['crop'].upper()}_PRICE_{cmp.upper()}_{_fmt(K)}", "price", s["crop"], "price_usd_bu", cmp, K, price,
                f"price_{cmp}_{int(round(m * 100))}")

    df = pd.DataFrame(rows).drop_duplicates("contract_id")
    yes = np.column_stack(cols)[:, df.index.to_numpy()]
    df = df.reset_index(drop=True)
    p = yes.mean(axis=0)
    df["p_yes"] = p
    # Whole cents (rounded up), like real Kalshi quotes, so the frontend prices identically.
    df["ask_yes"] = np.minimum(0.99, np.ceil((p + s["ask_markup"]) * 100 - 1e-9) / 100)
    df["ask_no"] = np.minimum(0.99, np.ceil(((1 - p) + s["ask_markup"]) * 100 - 1e-9) / 100)
    df["hypothetical"] = True
    return df, yes


def sides(contracts: pd.DataFrame, yes: np.ndarray) -> tuple[pd.DataFrame, np.ndarray]:
    """Expand to contract-sides: (sides table with side/ask/fair_value, payoff matrix N x 2K).
    Sides that never pay (p = 0) are dropped: they can't hedge anything."""
    t = pd.concat([contracts.assign(side="YES", ask=contracts.ask_yes, fair_value=contracts.p_yes),
                   contracts.assign(side="NO", ask=contracts.ask_no, fair_value=1 - contracts.p_yes)],
                  ignore_index=True)
    pay = np.concatenate([yes, 1 - yes], axis=1).astype(np.int8)
    keep = (t["fair_value"] > 0).to_numpy()
    return t[keep].reset_index(drop=True), pay[:, keep]
