# Farmer Joe — Frontend Integration Spec

Connect the team's web frontend (GitHub `sidterminator/Farmer-Joe`, branch `lingbo-z`, folder
`frontend/`) to our backend (weather model + hedge model in this folder). Build in steps; after
each, run checks, show results, stop for review.

---

## 1. What the Frontend Is (Read Before Coding)

- Plain HTML/CSS/JS in `frontend/`, no build step, three screens: `#/` intro, `#/farm` form with a
  map pin, `#/plan` advice screen with a revenue-by-harvest chart and hedge "tickets."
- **Single data seam:** `FarmerJoe.source.scenario(farm)` in `frontend/sample-data.js`, returning a
  Promise. Today it returns **deliberately exaggerated sample data** (its README says so). We
  replace it with a call to our server and keep the shape.
- Current shape returned by `scenario()`:
  ```
  { sample, exaggerated, seasons,
    farmShock: Float64Array(seasons),          // standardized farm yield shock per season
    markets: [{ id, name, preselect, question, caveat?, yesCents, noCents,
                payoutYes: Uint8Array(seasons) }] }
  ```
  `app.js` (`enterPlan`, ~line 455) turns `farmShock` into revenue with `M.farmIncome(...)`, then
  the client-side adviser (`advisor.js` → `model.recommend`) sizes hedges inside the budget and
  re-sizes whenever the farmer ticks, unticks, or switches sides.
- The farm object available in `app.js`: `state.farm` with `lat, lon, crop, acres, yield, price,
  budget, lean` (lean 1–5 → stability 0.2–1 via `LEAN`), `stationId`; stations in
  `frontend/stations.js` (38 Kalshi cities with real series tickers, approximate coordinates).
- The `lingbo-z` branch also contains **unrelated leftover code** from a previous project
  (`app.py`, `bizfax/`, `tests/test_core.py`, `requirements.txt`). It must not ship.

---

## 2. Architecture

```
browser (frontend/)  ──POST /api/scenario──▶  server.py (FastAPI, our repo)
                                               ├─ run_weather(settings)   (cached per farm+crop)
                                               └─ run_hedge(run_id, farmer inputs)
                     ◀── JSON scenario ────────
```

- `server.py` serves `frontend/` as static files AND the API from the same origin
  (`http://localhost:8000`), so no CORS setup is needed.
- Run: `.venv/bin/uvicorn server:app --port 8000`, then open `http://localhost:8000`.
- The frontend must still open from disk with sample data if the server is not running
  (fallback), so the demo never shows a blank screen.

---

## 3. API Contract

`POST /api/scenario`
Request JSON: `{ lat, lon, crop, acres, yield, price, budget, stability, stationId }`

Response JSON:
```
{
  "sample": false,
  "exaggerated": false,
  "seasons": 10000,
  "revenue": [ ... 10000 numbers, USD, unhedged farm revenue per scenario ... ],
  "markets": [
    { "id": "rain_lt_p20", "name": "Rain", "question": "Chicago July rain below 2.4 in",
      "caveat": "Hypothetical contract", "yesCents": 23, "noCents": 77,
      "preselect": true,
      "payoutYes": "<base64 of 10000 bytes, 0/1>" },
    ...
  ],
  "recommendation": {
    "decision": "hedge" | "partial" | "none",
    "reason": "one line",
    "picks": [ { "id": "...", "side": "yes"|"no", "contracts": 12000, "dollars": 3000,
                 "maxCents": 28 } ]
  },
  "meta": { "station": "...", "stationMiles": 135, "naturalHedgePct": 11.9,
            "placeholders": true, "runId": "..." }
}
```
- `markets` = the hedge model's contract menu (HEDGE_MODEL.md §4) with prices = synthetic ask
  (fair value + $0.03) in cents for each side. `preselect` = true for the model's recommended legs.
- `payoutYes` base64 keeps the payload small; decode to `Uint8Array` in the browser.
- Use the frontend's 38-station list (`frontend/stations.js`) as the backend's list of market
  stations (single source of truth): load it in Python by parsing the JS array, or move it to
  `frontend/stations.json` and have both sides read that.

---

## 4. Frontend Changes (Minimal)

1. `sample-data.js`: `source.scenario(farm)` → `fetch('/api/scenario', POST farm)`; decode base64
   payouts to `Uint8Array`, `revenue` to `Float64Array`. On any error or when opened from
   `file://`, fall back to the existing `buildScenario(farm)` and keep the "Sample data" labels.
   Pass `lat, lon` and the farmer's inputs (the farm object in `enterPlan` must include them).
2. `app.js` `enterPlan`: if `scenario.revenue` exists, use it directly instead of
   `M.farmIncome(...)`.
3. Initial plan = the backend's `recommendation.picks` (tick those markets, set sides and
   contracts). After that, keep the existing client-side re-sizing when the farmer edits.
4. Show the backend verdict as one line on the advice screen: "Hedge", "Partial hedge", or
   "Don't hedge — <reason>". If "none", start with nothing ticked.
5. When data is real: hide "Sample data" notes; show "Model output — contracts are hypothetical,
   coefficients are placeholders. Educational tool, not financial advice." Keep the order button
   disabled.

---

## 5. Repo Plan (Git)

1. Add the GitHub repo as a remote; fetch `main` and `lingbo-z`.
2. Create branch `integration` from `lingbo-z`. Delete the leftover `bizfax` files (`app.py`,
   `bizfax/`, `tests/test_core.py`, old `requirements.txt`).
3. Add our backend (package, `run.py`, `server.py`, specs, config, tests, `app/` dashboard,
   requirements). Keep `data/` and `outputs/` git-ignored, except a small cached demo dataset if
   needed for offline demo (ask first).
4. Write a top-level README: what it is, how to run (`uvicorn` + open browser), what is real vs
   placeholder.
5. Push `integration` and open a pull request to `main`. Do not push to `main` directly. Do not
   rewrite teammates' history. If pushing fails for permissions, stop and tell me.

---

## 6. Acceptance Checks

- `pytest -q` passes (all backend tests).
- `/api/scenario` returns the contract above for the three test farms in < 10 s warm (cache).
- In the browser: farm form → advice screen shows real revenue, the backend's preselected legs and
  verdict; ticking/unticking still re-sizes; budget warning still works.
- With the server stopped, opening `frontend/index.html` still works on sample data.
- No `bizfax` code remains on the `integration` branch.
