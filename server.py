"""Farmer Joe web server: the frontend (static files) and the model API on one origin.

    .venv/bin/uvicorn server:app --port 8000      # then open http://localhost:8000

POST /api/scenario  {lat, lon, crop, acres, yield, price, budget, stability, stationId}
 -> weather run (cached per 0.1-degree grid cell + crop) -> hedge model v1 -> JSON in the shape the
    frontend's `FarmerJoe.source.scenario()` expects (docs/INTEGRATION.md §3).
"""
from __future__ import annotations

import base64
import calendar
import math
import time
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from farmerjoe.webcache import weather_run
from farmerjoe.hedge.pipeline import run_hedge
from farmerjoe.hedge.settings import load_hedge_settings
from farmerjoe.stations import haversine_km

ROOT = Path(__file__).resolve().parent
KM_PER_MILE = 1.609344

app = FastAPI(title="Farmer Joe")


class FarmIn(BaseModel):
    lat: float = Field(ge=24, le=50)       # contiguous US
    lon: float = Field(ge=-125, le=-66)
    crop: str
    acres: float = Field(gt=0)
    yield_: float = Field(gt=0, alias="yield")
    price: float = Field(gt=0)
    budget: float = Field(ge=0)
    stability: float = Field(ge=0, le=1)  # frontend "lean" 0.2..1 -> risk weight
    stationId: str | None = None


def _window_label(start: str, end: str) -> str:
    m0, m1 = int(start[5:7]), int(end[5:7])
    return calendar.month_name[m0] if m0 == m1 else f"{calendar.month_abbr[m0]}–{calendar.month_abbr[m1]}"


def _market(row, yes_col: np.ndarray, city: dict, crop: str, window: str, preselect: bool) -> dict:
    t = row.threshold
    if row.family == "rain":
        where = city.get(row.location, row.location)
        q = f"{where} {window} rain {'below' if row.comparator == 'lt' else 'at least'} {t:.1f} in"
        name = f"{where} rain {'<' if row.comparator == 'lt' else '≥'}{t:.1f} in"
    elif row.family == "heat":
        where = city.get(row.location, row.location)
        q = f"{where} has {int(t)}+ days at 95°F or hotter in {window}"
        name = f"{where} heat ≥{int(t)}d"
    else:
        q = f"{crop.capitalize()} harvest price {'below' if row.comparator == 'lt' else 'at or above'} ${t:.2f}/bu"
        name = f"Price {'<' if row.comparator == 'lt' else '≥'}${t:.2f}"
    return {"id": row.key, "name": name, "question": q,
            "caveat": "Hypothetical contract" + ("; may not exist on Kalshi" if row.family == "price" else ""),
            "yesCents": int(round(row.ask_yes * 100)),   # asks are whole cents already
            "noCents": int(round(row.ask_no * 100)),
            "preselect": bool(preselect),
            "payoutYes": base64.b64encode(np.ascontiguousarray(yes_col, dtype=np.uint8).tobytes()).decode()}


PRICE_BAND = (0.5, 2.0)        # plausible futures price vs the crop's reference price in config
STRIKE_BAND = 0.30             # price-contract strikes within +-30% of the futures price used
REVENUE_TOL = 0.25             # mean revenue within 25% of acres x yield x price


def check_price_input(farm: "FarmIn") -> None:
    """Reject a price that cannot belong to this crop (e.g. a soybean price sent for corn)."""
    ref = load_hedge_settings(farm.crop)["futures_price_usd_bu"]
    lo, hi = PRICE_BAND[0] * ref, PRICE_BAND[1] * ref
    if not lo <= farm.price <= hi:
        raise HTTPException(422, f"Price ${farm.price:.2f}/bu is not plausible for {farm.crop} "
                                 f"(reference ${ref:.2f}/bu; allowed ${lo:.2f}-${hi:.2f}). "
                                 f"Check that the price matches the crop.")


def check_outputs(farm: "FarmIn", res: dict) -> None:
    """Consistency checks on the model output before it reaches the screen."""
    F = res["settings"]["futures_price_usd_bu"]
    c = res["contracts"]
    strikes = c.loc[c.family == "price", "threshold"].to_numpy()
    bad = strikes[np.abs(strikes / F - 1) > STRIKE_BAND + 1e-9]
    if len(bad):
        raise HTTPException(500, f"Sanity check failed: price strikes {sorted(set(bad.round(2)))} are more than "
                                 f"{STRIKE_BAND:.0%} from the futures price ${F:.2f}.")
    expected = farm.acres * farm.yield_ * farm.price
    mean_rev = float(res["rev"]["revenue_usd"].mean())
    if abs(mean_rev / expected - 1) > REVENUE_TOL:
        raise HTTPException(500, f"Sanity check failed: mean revenue ${mean_rev:,.0f} is more than "
                                 f"{REVENUE_TOL:.0%} from acres x yield x price = ${expected:,.0f}.")


@app.post("/api/scenario")
def scenario(farm: FarmIn) -> dict:
    t0 = time.perf_counter()
    if farm.crop not in ("corn", "soybeans", "wheat"):
        raise HTTPException(422, f"crop must be corn, soybeans or wheat (got {farm.crop!r})")
    check_price_input(farm)
    run_dir, cfg = weather_run(farm.lat, farm.lon, farm.crop)
    res = run_hedge(run_dir, {"acres": farm.acres, "aph_yield_bu_ac": farm.yield_,
                              "futures_price_usd_bu": farm.price, "budget_usd": farm.budget,
                              "risk_weight": farm.stability}, write=False)
    meta, rec, contracts, yes = res["meta"], res["rec"], res["contracts"], res["yes"]
    check_outputs(farm, res)
    city = {code: m["city"] for code, m in cfg.market_stations.items()}
    picked = {r["key"] for r in rec["legs"]}
    window = _window_label(meta["window"]["start"], meta["window"]["end"])
    markets = [_market(row, yes[:, i], city, farm.crop, window, row.key in picked)
               for i, row in enumerate(contracts.itertuples())]

    st_code = (farm.stationId or "").upper()
    st = cfg.market_stations.get(st_code)
    if st is None:   # fall back to the nearest selected station
        s0 = meta["station_info"][0]
        st_code, st = s0["code"], cfg.market_stations[s0["code"]]
    miles = float(haversine_km(farm.lat, farm.lon, st["lat"], st["lon"])) / KM_PER_MILE

    return {
        "sample": False,
        "exaggerated": False,
        "seasons": int(len(res["rev"])),
        "revenue": np.round(res["rev"]["revenue_usd"].to_numpy(), 0).tolist(),
        "markets": markets,
        "recommendation": {
            "decision": rec["decision"],
            "reason": rec["reason"],
            "picks": [{"id": r["key"], "side": r["side"].lower(), "contracts": int(r["contracts"]),
                       "dollars": round(r["dollars"], 2), "maxCents": int(math.floor(r["max_entry_price"] * 100))}
                      for r in rec["legs"]],
            "bestAvailable": None if not rec.get("best_available") else {
                "id": rec["best_available"]["key"], "side": rec["best_available"]["side"].lower(),
                "contracts": rec["best_available"]["contracts"]},
        },
        "meta": {
            "station": st["city"], "stationMiles": round(miles),
            "naturalHedgePct": round(100 * res["nh"]["natural_hedge_pct"], 1),
            "placeholders": True, "runId": meta["run_id"], "crop": farm.crop,
            "yieldTrend": float(res["settings"].get("chart_yield_trend", 0.015)),
            "window": meta["window"],
            "modelStations": [{"code": s["code"], "city": city.get(s["code"], s["code"]),
                               "miles": round(s["distance_km"] / KM_PER_MILE), "seasons": s["record_years"]}
                              for s in meta["station_info"]],
            "evalHalf": {k: rec["eval_half"][k] for k in ("delta_cvar5", "cost", "shortfall")},
            "seconds": round(time.perf_counter() - t0, 2),
        },
    }


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.middleware("http")
async def revalidate_static(request, call_next):
    """Make browsers re-check frontend files on every load (cheap: ETag -> 304), so an updated
    app.js / styles.css is never served from a stale cache during a demo."""
    response = await call_next(request)
    if not request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


# Static frontend last, so /api routes win. html=True serves index.html at "/".
app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
