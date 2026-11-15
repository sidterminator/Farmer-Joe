"""Pick the cheapest carrier whose P90 arrival is on or before the deadline."""
from __future__ import annotations

import datetime as dt


def recommend(rows: list[dict], deadline: dt.date) -> dict:
    """rows: dicts with keys carrier, price_usd, p50, p90.

    Returns {"pick": row | None, "reason": str}.
    """
    ok = [r for r in rows if r["p90"] <= deadline]
    if ok:
        pick = min(ok, key=lambda r: r["price_usd"])
        return {"pick": pick, "reason": f"Cheapest carrier with 90% confidence of arriving by {deadline:%b %d}."}
    if not rows:
        return {"pick": None, "reason": "No carriers available."}
    nearest = min(rows, key=lambda r: r["p90"])
    return {"pick": None, "reason": (
        f"No carrier reliably makes {deadline:%b %d}. Closest: {nearest['carrier']}, "
        f"90% confident by {nearest['p90']:%b %d}.")}
