"""Hedge search (HEDGE_MODEL.md §5-6): single leg, greedy multi-leg, entry prices, decision.

PL_i = revenue_i + n * (payout_i - ask); score = (1 - w) mean(PL) + w CVaR_alpha(PL),
CVaR = average of the worst alpha share. Choose on the train half, report on the eval half.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def cvar(x: np.ndarray, alpha: float = 0.05, axis: int = 0) -> np.ndarray:
    """Average of the worst alpha share along `axis` (lower tail)."""
    k = max(1, int(np.ceil(alpha * x.shape[axis])))
    part = np.partition(x, k - 1, axis=axis)
    return np.take(part, range(k), axis=axis).mean(axis=axis)


def score(pl: np.ndarray, w: float, alpha: float = 0.05, axis: int = 0) -> np.ndarray:
    return (1 - w) * pl.mean(axis=axis) + w * cvar(pl, alpha, axis)


def size_grid(ask: float, budget: float, steps: int, lot: int) -> np.ndarray:
    """0 .. budget/ask in `steps` steps, rounded down to lots, unique."""
    n_max = np.floor(budget / ask / lot) * lot
    g = np.floor(np.linspace(0, n_max, steps + 1) / lot) * lot
    return np.unique(g)


def single_leg_search(revenue: np.ndarray, payoffs: np.ndarray, asks: np.ndarray, budget: float,
                      w: float, train: np.ndarray, alpha: float = 0.05, steps: int = 40,
                      lot: int = 100) -> dict[str, Any]:
    """Best (side j, size n) on the train scenarios. Returns j, n, score, and the
    no-hedge score. Budget: n * ask <= budget by construction of the grid."""
    r = revenue[train]
    base = float(score(r, w, alpha))
    best = {"j": None, "n": 0.0, "score": base, "base_score": base}
    for j in range(payoffs.shape[1]):
        g = size_grid(asks[j], budget, steps, lot)
        if len(g) < 2:
            continue
        pl = r[:, None] + g[None, :] * (payoffs[train, j][:, None] - asks[j])   # (n_train, grid)
        sc = score(pl, w, alpha, axis=0)
        k = int(np.argmax(sc))
        if sc[k] > best["score"] + 1e-9:
            best = {"j": j, "n": float(g[k]), "score": float(sc[k]), "base_score": base}
    return best


def summarize(pl: np.ndarray, alpha: float = 0.05) -> dict[str, float]:
    return {"mean": float(pl.mean()), "sd": float(pl.std()), "p5": float(np.percentile(pl, 5)),
            "cvar5": float(cvar(pl, alpha))}


def evaluate(revenue: np.ndarray, payoffs: np.ndarray, asks: np.ndarray, legs: list[tuple[int, float]],
             idx: np.ndarray, alpha: float = 0.05) -> dict[str, Any]:
    """Unhedged vs hedged stats on scenarios `idx` (the evaluation half)."""
    r = revenue[idx]
    pl = r.copy()
    for j, n in legs:
        pl = pl + n * (payoffs[idx, j] - asks[j])
    before, after = summarize(r, alpha), summarize(pl, alpha)
    return {"before": before, "after": after, "delta_cvar5": after["cvar5"] - before["cvar5"],
            "cost": before["mean"] - after["mean"], "shortfall": before["mean"] - before["cvar5"]}


def _pl(revenue: np.ndarray, payoffs: np.ndarray, asks: np.ndarray, legs: list[tuple[int, float]],
        idx: np.ndarray, skip: int | None = None) -> np.ndarray:
    out = revenue[idx].astype(float).copy()
    for k, (j, n) in enumerate(legs):
        if k != skip and n:
            out += n * (payoffs[idx, j] - asks[j])
    return out


def _best_size(base: np.ndarray, pay_j: np.ndarray, ask: float, budget_left: float, w: float,
               alpha: float, steps: int, lot: int) -> tuple[float, float]:
    """Best size for one leg on top of `base` PL (train rows); returns (n, score)."""
    g = size_grid(ask, max(budget_left, 0.0), steps, lot)
    pl = base[:, None] + g[None, :] * (pay_j[:, None] - ask)
    sc = score(pl, w, alpha, axis=0)
    k = int(np.argmax(sc))
    return float(g[k]), float(sc[k])


def greedy_search(revenue: np.ndarray, payoffs: np.ndarray, asks: np.ndarray, contract_of: np.ndarray,
                  budget: float, w: float, train: np.ndarray, max_legs: int = 3, alpha: float = 0.05,
                  steps: int = 40, lot: int = 100, min_gain_frac: float = 0.02) -> dict[str, Any]:
    """HEDGE_MODEL §5: best single leg, then add legs greedily (re-size the new leg with the
    others fixed, then one pass re-sizing every leg). Stop when the gain is < 2% of the gain
    so far. Budget: sum(n * ask) <= budget. Never both sides of one contract
    (`contract_of[j]` = contract index of side j)."""
    base_score = float(score(revenue[train], w, alpha))
    legs: list[tuple[int, float]] = []
    cur = base_score
    while len(legs) < max_legs:
        spent = sum(n * asks[j] for j, n in legs)
        used = {contract_of[j] for j, _ in legs}
        base = _pl(revenue, payoffs, asks, legs, train)
        best = (None, 0.0, cur)
        for j in range(payoffs.shape[1]):
            if contract_of[j] in used:
                continue
            n, sc = _best_size(base, payoffs[train, j], asks[j], budget - spent, w, alpha, steps, lot)
            if n > 0 and sc > best[2]:
                best = (j, n, sc)
        if best[0] is None:
            break
        gain_so_far = cur - base_score
        if legs and best[2] - cur < min_gain_frac * gain_so_far:
            break
        legs.append((best[0], best[1]))
        # one pass re-sizing every leg with the others fixed
        for k in range(len(legs)):
            j = legs[k][0]
            others = sum(n * asks[jj] for kk, (jj, n) in enumerate(legs) if kk != k)
            base_k = _pl(revenue, payoffs, asks, legs, train, skip=k)
            n, _ = _best_size(base_k, payoffs[train, j], asks[j], budget - others, w, alpha, steps, lot)
            legs[k] = (j, n)
        legs = [(j, n) for j, n in legs if n > 0]
        cur = float(score(_pl(revenue, payoffs, asks, legs, train), w, alpha))
    return {"legs": legs, "score": cur, "base_score": base_score}


def max_entry_price(revenue: np.ndarray, payoffs: np.ndarray, asks: np.ndarray, legs: list[tuple[int, float]],
                    k: int, budget: float, w: float, train: np.ndarray, alpha: float = 0.05, steps: int = 40,
                    lot: int = 100, min_leg: int = 100, iters: int = 12) -> float:
    """Highest ask at which leg k would still be bought (n >= min_leg) when re-sized with the
    other legs fixed (bisection on the ask)."""
    j = legs[k][0]
    others = sum(n * asks[jj] for kk, (jj, n) in enumerate(legs) if kk != k)
    base = _pl(revenue, payoffs, asks, legs, train, skip=k)

    def buys(a: float) -> bool:
        n, _ = _best_size(base, payoffs[train, j], a, budget - others, w, alpha, steps, lot)
        return n >= min_leg

    lo, hi = float(asks[j]), 0.99
    if not buys(lo):
        return lo
    if buys(hi):
        return hi
    for _ in range(iters):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if buys(mid) else (lo, mid)
    return lo


def decide(ev: dict[str, Any], natural_hedge_pct: float, max_he: float | None, rule: dict[str, float]) -> tuple[str, str]:
    """HEDGE_MODEL §6 on the evaluation half -> (decision, one-line reason)."""
    mean = ev["before"]["mean"]
    short = ev["shortfall"]
    dc = ev["delta_cvar5"] / short if short > 0 else 0.0
    cost = ev["cost"] / mean if mean else 0.0
    if dc >= rule["hedge_dcvar_min"] and cost <= rule["hedge_cost_max"]:
        return "hedge", f"Raises the bad-year income by {dc:.0%} of the shortfall for {cost:.1%} of average revenue."
    if dc >= rule["partial_dcvar_min"] and cost <= rule["partial_cost_max"]:
        return "partial", (f"Helps some (+{dc:.0%} of the bad-year shortfall, cost {cost:.1%} of revenue); "
                           f"buy half the suggested amounts.")
    if short < 0.10 * mean:
        return "none", "Exposure is small: bad years are close to average years."
    if dc >= rule["partial_dcvar_min"]:
        return "none", f"Protection is too expensive: {cost:.1%} of average revenue."
    if natural_hedge_pct >= 0.15:
        return "none", f"The natural hedge already steadies income ({natural_hedge_pct:.0%} less swing)."
    he = "" if max_he is None else f" (weather contracts explain at most {max_he:.0%} of farm rain)"
    return "none", "Weak link between the farm and the contract stations" + he + "."
