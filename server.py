"""Farmer Joe web server: the frontend (static files) and the model API on one origin.

    .venv/bin/uvicorn server:app --port 8000      # then open http://localhost:8000

POST /api/scenario  {lat, lon, crop, acres, yield, price, budget, stability, stationId}
 -> weather run (cached per farm location + crop) -> hedge model v1 -> JSON in the shape the
    frontend's `FarmerJoe.source.scenario()` expects (docs/INTEGRATION.md §3).
"""
from __future__ import annotations

import base64
import calendar
import math
import threading
import time
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import run as weather_cli
from farmerjoe.config import load_config
from farmerjoe.hedge.pipeline import run_hedge
from farmerjoe.stations import haversine_km

ROOT = Path(__file__).resolve().parent
WEB_RUNS = ROOT / "outputs" / "web"
KM_PER_MILE = 1.609344

app = FastAPI(title="Farmer Joe")
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


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


def weather_run(lat: float, lon: float, crop: str) -> tuple[Path, object]:
    """Weather run for this farm + crop, cached on disk (location rounded to 0.01 deg ~ 1 km)."""
    lat, lon = round(lat, 2), round(lon, 2)
    run_id = f"web_{crop}_{lat:.2f}_{lon:.2f}"
    out_dir = WEB_RUNS / run_id
    cfg = load_config(overrides={"lat": lat, "lon": lon, "crop": crop, "mode": "climatology",
                                 "output_dir": str(WEB_RUNS)})
    with _locks_guard:
        lock = _locks.setdefault(run_id, threading.Lock())
    with lock:
        if not (out_dir / "run_meta.json").exists():
            rng = np.random.default_rng(cfg.seed)
            weather_cli.run_joint(cfg, out_dir, run_id, rng, refit=False, skip_validation=True)
    return out_dir, cfg


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


@app.post("/api/scenario")
def scenario(farm: FarmIn) -> dict:
    t0 = time.perf_counter()
    if farm.crop not in ("corn", "soybeans", "wheat"):
        raise HTTPException(422, f"crop must be corn, soybeans or wheat (got {farm.crop!r})")
    run_dir, cfg = weather_run(farm.lat, farm.lon, farm.crop)
    res = run_hedge(run_dir, {"acres": farm.acres, "aph_yield_bu_ac": farm.yield_,
                              "futures_price_usd_bu": farm.price, "budget_usd": farm.budget,
                              "risk_weight": farm.stability}, write=False)
    meta, rec, contracts, yes = res["meta"], res["rec"], res["contracts"], res["yes"]
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
        },
        "meta": {
            "station": st["city"], "stationMiles": round(miles),
            "naturalHedgePct": round(100 * res["nh"]["natural_hedge_pct"], 1),
            "placeholders": True, "runId": meta["run_id"], "crop": farm.crop,
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


# Static frontend last, so /api routes win. html=True serves index.html at "/".
app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
