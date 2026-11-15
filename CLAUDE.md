# Farmer Joe — Weather Model Build Spec

This file is the source of truth for the weather model. Read it fully before writing code.
Build **one phase at a time** (see "Build Phases"). After each phase, run its acceptance
checks, show the results (numbers + plots), and stop for review before starting the next.

---

## 1. Goal

A tool that helps **farmers anywhere in the US** hedge weather risk with prediction-market
contracts (Kalshi).

This file specifies the **weather model**. It takes a farm location and a crop (which sets the
default season window), picks the nearest stations where contracts settle, and outputs
thousands of simulated weather scenarios for the farm, those settlement stations, and the
crop's production-region index locations. The hedge model (`docs/HEDGE_MODEL.md`, v1) turns those
scenarios into revenue and recommends a hedge; `docs/REVENUE_MODEL.md` and `docs/OPTIMIZER.md` are its
v2 replacements. All live in this repo; the output files below are the interface between them.

### Build Order (Solo)

One person builds everything, in this order. This overrides the phase order in each spec.
1. **Weather model:** Phase 2 (§11), including nationwide station selection, the crop
   calendar, production-region index locations, and the trend switch. *(done, review open)*
2. **Hedge model v1:** `docs/HEDGE_MODEL.md` H0–H2 (rule-based yield, price with the natural hedge,
   synthetic contract menu, greedy 1–3 leg search, entry prices, hedge-or-not, `--mode hedge`).
3. **Dashboard:** `docs/HEDGE_MODEL.md` H3 (the hedge section of the Streamlit app, §13).
4. Stretch: Phases 3–4 here (forecast).

**v2 ideas, not scheduled:** `docs/REVENUE_MODEL.md` (fitted yield + price models) and `docs/OPTIMIZER.md`
(MILP optimizer, leg frontier, strategy comparison) replace the v1 hedge model later. Also not
scheduled: Phases 5–6 here (including the 6.7 hierarchical option). Every step still stops for
review after its acceptance checks.

**Model in one line:** climatology prior + calibrated ensemble forecast (Bayesian) →
Monte Carlo simulation of N day-by-day seasons → scenario tables + contract probabilities.

---

## 2. Scope (Do Not Expand Without Asking)

- Farms: **any US location** (lat/lon). Reference farms used in acceptance tests:
  - `champaign_corn`: corn, central Illinois, lat 40.1, lon -88.2 (config default).
  - `salina_wheat`: winter wheat, central Kansas, lat 38.8, lon -97.6.
- Crops: `corn`, `soybeans`, `wheat` (hard red winter by default; soft red winter via
  config), matching `docs/REVENUE_MODEL.md`. The crop calendar (6.0) sets the season window;
  `--start/--end` override it.
- Settlement stations: selected automatically as the K nearest (default 3) **market
  stations**, meaning stations with tradeable contracts, from the configurable list
  `market_stations` in `config.yaml`. Each entry says which markets it has (`rain`, `tmax`)
  and whether it has been confirmed against Kalshi listings (`verified_market`). `--stations`
  overrides the selection. GHCN IDs are looked up automatically (5) and verified by name +
  coordinates; never hard-code an unverified ID. Verified so far: ORD `USW00094846`, MDW
  `USW00014819`.
- Production-region index locations for the crop (6.8) are simulated jointly with the farm
  and stations, as the revenue model's national-supply driver (`docs/REVENUE_MODEL.md` §9).
- Variables (daily): `tmax_f`, `tmin_f`, `precip_in`.
- Units: °F and inches everywhere. Dates are local to the farm (IANA zone from Open-Meteo
  `timezone=auto`). NWS/GHCN daily values follow each station's local standard time; a station
  in another zone is offset by < 1 day, which we accept and note in code comments where daily
  aggregation happens.

---

## 3. Conventions

- Python 3.11+. Dependencies: numpy, pandas, scipy, matplotlib, requests, pyarrow, pyyaml, pymc,
  arviz, properscoring, pytest (+ streamlit for §13). Put them in `requirements.txt`; exact
  tested versions go in `requirements-lock.txt`.
- **Always use the project virtual environment `.venv`** (`.venv/bin/python`,
  `.venv/bin/python -m pytest`). Never `pip install` into the global Python.
- **Randomness:** one `np.random.default_rng(seed)` created in `run.py` and passed down.
  Never use global `np.random.*` state.
- **Vectorize:** simulate arrays of shape `(N, D)` (scenarios × days) or `(N, D, L)` (+ locations).
  Only loop over days where AR(1)/Markov recursion requires it. Never loop over scenarios.
- **Cache every download** to `data/raw/` as parquet. Fetch functions check the cache first.
  Add `data/` to `.gitignore`.
- Fitted parameters are saved to `data/params/*.json` so simulation doesn't refit each run.
- Config lives in `config.yaml`; `run.py` CLI flags override it.
- Type hints and short docstrings on public functions. Keep functions small and testable.
- Never shuffle across time when splitting train/test. Hold out the most recent 5 years.

---

## 4. Repo Structure

```
Farmer Joe/
  CLAUDE.md
  requirements.txt
  config.yaml
  run.py                     # CLI entry point
  farmerjoe/
    __init__.py
    config.py                # load config.yaml + CLI overrides
    stations.py              # market-station list, GHCN ID lookup, nearest-K selection, distances
    crops.py                 # crop calendar → season window (table in config.yaml)
    regions.py               # production-region index locations (points per region)
    fetch/
      history.py             # daily observations (station + farm)
      station_meta.py        # GHCN station list + inventory (cached)
      ensemble.py            # today's ensemble forecast
      hindcasts.py           # historical forecasts for calibration
    model/
      climatology.py         # fit Normal / Bernoulli / Gamma / AR(1) / Markov params
      dependence.py          # farm–station correlations, latent-Gaussian copula
      calibrate_temp.py      # EMOS: MLE first, then PyMC
      calibrate_rain.py      # logistic P(wet) + Gamma amounts on forecast
      hierarchical.py        # Phase 5 option: partial pooling across nearby stations
      simulate.py            # Monte Carlo engine
    outputs/
      schema.py              # column specs + validate_*() functions
      aggregate.py           # daily → season totals (R, H, GDD)
      contracts.py           # contract_probs + payoff_matrix()
      hedge.py               # hedge_effectiveness() + hedge_diagnostics (shared with optimizer)
      write.py               # assemble + validate + write a run
      fake.py                # fake-data generator in the exact output schema
    validate/
      scores.py              # Brier, CRPS, PIT, reliability
      backtest.py
      plots.py
  tests/
    test_schema.py
    test_synthetic.py        # known-truth recovery tests
    test_simulate.py
    test_stations.py         # GHCN metadata parsing, distances, nearest-K selection
    test_crops.py            # crop calendar resolution
    test_hedge.py            # hedge effectiveness on known-R² synthetic data
  app/
    streamlit_app.py         # §13
  data/                      # cache (gitignored)
  outputs/                   # run outputs (gitignored)
```

---

## 5. Data Sources (Verify Exact Parameters Against Live Docs)

**Station observations — NOAA NCEI Access Data Service (GHCN-Daily)**
`https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=<ID>&startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&dataTypes=TMAX,TMIN,PRCP&units=standard&format=json`
Request in chunks (e.g., 5 years) to avoid size limits. Handle missing values and flags.

**GHCN station metadata — NCEI** (for automatic station-ID lookup)
`https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt` (fixed-width: ID, lat, lon,
elevation, state, name) and `ghcnd-inventory.txt` (ID, lat, lon, element, first year, last
year). Cache both in `data/raw/`. Resolve each market station to a GHCN ID by matching
coordinates/name, preferring `USW` first-order stations with TMAX, TMIN, PRCP covering the
history window. Confirm via the Access Data Service (`includeStationName=true`: name + coords
must match) and store the result in `data/params/stations_resolved.json`.

**Farm-location history — Open-Meteo Historical Weather (archive) API**
`https://archive-api.open-meteo.com/v1/archive` with `latitude, longitude, start_date, end_date,
daily=temperature_2m_max,temperature_2m_min,precipitation_sum, temperature_unit=fahrenheit,
precipitation_unit=inch, timezone=America/Chicago`.
Note: this is gridded reanalysis, not a station. Fine for the farm. The same API supplies the
history at production-region index points (6.8).

**Ensemble forecast — Open-Meteo Ensemble API**
`https://ensemble-api.open-meteo.com/v1/ensemble` with `models=ecmwf_ifs025` (also try
`gfs_seamless`), hourly `temperature_2m,precipitation`, fahrenheit/inch, timezone America/Chicago.
Returns one column per member. Aggregate hourly → daily (max, min, sum) per member.

**Historical forecasts (for calibration) — Open-Meteo Historical Forecast API / Previous Runs API**
Deterministic (single best-guess) past forecasts. Pair forecast-for-day-d made at lead L with
the observation on day d, for L = 1..14. Ensemble hindcasts are hard to get; using deterministic
forecasts to learn bias and error size per lead time is the accepted shortcut here.

Standard history window: 1995–2024 (30 years). Stations with shorter records (e.g., MDW: GHCN
temperature from 1997, rain from 1998) use what exists; flag `short_record` in run_meta when a
station has < 20 complete seasons in the fit years. All fetchers return a DataFrame with columns
`date, tmax_f, tmin_f, precip_in` (plus `member` / `lead_days` / `issue_date` where relevant).

---

## 6. Model Specification

### 6.0 Crop Calendar — `crops.py` (table in `config.yaml`)

Defaults from `docs/REVENUE_MODEL.md` §4 (one window per crop, used for every location):

| crop | critical weather window (season window) | harvest price window |
|---|---|---|
| corn | Jul (pollination) | Oct |
| soybeans | Aug (pod fill) | Oct |
| wheat (HRW) | Apr–May (heading, grain fill) | Jul |

- Windows are **whole calendar months**, so they line up with monthly contract settlement,
  and may not cross Dec 31. The season year is `--year` (default: next season not yet
  started).
- The harvest price window is used by the revenue model, not here; it lives in the same table
  so there is one calendar.
- An unknown crop is an error that lists the valid options. Never silently fall back to a
  default.
- `--start/--end` override the calendar; run_meta records `season_window_source`
  (`crop_calendar` | `cli`).

### 6.1 Target Season Variables (per scenario, per location)

- `rain_total_in` = Σ daily precip over the window.
- `hot_days_95` = count of days with tmax ≥ 95°F.
- `gdd` = Σ max(0, (min(tmax, 86) + max(tmin, 50)) / 2 − 50)   (corn GDD, base 50, cap 86).

### 6.2 Climatology (the prior) — `climatology.py`

Fit from historical days within the window (± 7-day buffer allowed for more data), per location:

- Temperature: tmax ~ Normal(μ, σ²); tmin ~ Normal(μ, σ²). Start with one μ, σ for the whole
  window; optional upgrade: day-of-year μ_t, σ_t via smoothing.
- Temperature persistence: AR(1) coefficient ρ of standardized anomalies (lag-1 autocorrelation,
  computed within each year so years don't chain together).
- Tmax–tmin link: correlation of their same-day anomalies.
- Rain occurrence: wet if precip ≥ 0.01 in. p_wet, plus Markov transitions p01 = P(wet|dry
  yesterday), p11 = P(wet|wet yesterday).
- Rain amount on wet days: Gamma(k, θ) via `scipy.stats.gamma.fit(x, floc=0)`.
- Buffer default is 0 days (config `climatology.buffer_days`). At ORD a 7-day buffer pulls in
  wetter late-June days and biases July rain +6%.
- Interannual variability (config `climatology.interannual`, default on). Day-by-day models
  underestimate the year-to-year spread of season totals. Each simulated season therefore gets
  a temperature offset δ ~ N(0, τ²) (tmax and tmin correlated) with within-season sd
  sqrt(σ² − τ²), plus a mean-1 lognormal multiplier on rain amounts. τ and the multiplier sd
  are fit by method of moments to the training years' variance of season means and totals,
  clipped at 0.
- Linear trend switch (config `climatology.trend`, CLI `--trend/--no-trend`, default off until
  the Phase 2 holdout check decides). Each location gets a **separate** trend for tmax and for
  tmin: OLS of that variable's season mean on year over the fit years, giving
  μ(year) = α + β·(year − fit_end). The simulation uses μ at the target season year. σ, ρ and
  τ are then fit on the detrended values, so the trend isn't counted as variability. Rain has
  no trend. run_meta reports β (°F/decade) with its standard error per location and variable.
  Warn if the target year is more than 10 years past the last fit year.

### 6.3 Dependence / Joint Simulation — `dependence.py`

Simulate all locations jointly with a **latent Gaussian** model:

- Each location has latent standardized series for temperature and for rain.
- Over time: AR(1) with that location's ρ (temperature) and a rain-latent ρ_r chosen so the
  simulated p11 approximately matches the observed p11 (fit by simple search).
- Across locations: correlated innovations with a correlation matrix estimated from historical
  same-day anomalies (temperature) and normal scores of rain (rain).
- Map latent → observed:
  - temperature: value = μ + σ·z
  - rain (Gaussian copula with point mass at 0): u = Φ(z); if u < 1 − p_wet → 0;
    else amount = Gamma⁻¹((u − (1 − p_wet)) / p_wet; k, θ)

Phase 1 may use the simpler single-location Markov chain for rain; Phase 4 replaces it with this.

### 6.4 Forecast Calibration — `calibrate_temp.py`, `calibrate_rain.py`

Temperature EMOS, fitted separately for each lead time L = 1..14 and each location:
  obs ~ Normal(a_L + b_L · fcst, s_L²)

- Step A: maximum likelihood with `scipy.optimize.minimize` (optimize log s for positivity).
- Step B (Bayesian): PyMC model with priors a ~ Normal(0, 5), b ~ Normal(1, 0.5),
  s ~ HalfNormal(5). Sample with `pm.sample()`; save posterior draws (e.g., 2,000) to disk.
  Check r-hat < 1.01 and no divergences.

Applying it to today's ensemble: for each scenario i, draw posterior parameters (a, b, s)_i,
pick ensemble member m_i at random; center = a + b · member_value; total spread must reproduce
s_L (i.e., noise sd = sqrt(max(s_L² − ensemble_var, small))) so spread is not double-counted.
Document the choice in code.

Rain calibration per lead time:
- P(wet) = logistic(β0 + β1 · fcst_precip_transformed)  (e.g., use log1p(fcst) or wet-member fraction)
- amount | wet ~ Gamma(k, θ) with mean = γ0 + γ1 · fcst_amount (keep mean > 0).

Blending with climatology: days beyond the forecast horizon (> 14 days, or beyond available
lead) use climatology only. Days within it use the calibrated forecast. Optionally shrink toward
climatology as lead grows (precision weighting); log what you did.

### 6.5 Monte Carlo Engine — `simulate.py`

`simulate(config, params, ensemble, rng) -> daily DataFrame`
- N scenarios (default 10,000), D days, L locations.
- Steps per scenario (vectorized): draw calibration params → pick member → generate forecast-
  window days → generate remaining days from climatology/latent model with continuity from the
  last forecast day → assemble tmax, tmin, precip per location.
- Must run in < 30 s for N=10,000, D=61, L=9 (farm + 3 stations + 5 index locations) on a
  laptop.

### 6.6 Station Selection — `stations.py`

- Candidates: `market_stations` in config, each with code, lat/lon (or GHCN ID), and its
  markets (`rain`, `tmax`).
- Distance: haversine km from the farm. Select the K nearest (default 3, `--k-stations`)
  that have at least one market and enough history; warn when the nearest is farther than
  `max_station_km` (default 400).
- Report each selected station's `distance_km`, GHCN ID, name, record length and
  `short_record` in run_meta. Distance is reported, not used as a filter: hedge_diagnostics
  measures whether a far station is still useful.

### 6.7 Hierarchical Pooling (Phase 5 option) — `hierarchical.py`

Not scheduled in the solo build order. Partial pooling so short-record stations borrow
strength from neighbors. Off by default; enable with `--hierarchical`.
- Neighborhood: selected market stations + up to M (default 8) extra `USW` stations within
  R km (default 300) of the farm, plus the farm grid point.
- Climatology: two-stage (meta-analytic). Each location j has transformed parameters
  φ_j = (μ, log σ for tmax/tmin; atanh ρ; logit p01, logit p11; log k, log θ), with its own
  MLE φ̂_j and standard error SE_j. Model φ̂_j ~ N(φ_j, SE_j²), φ_j ~ N(m, τ²) per component.
  Use a non-centered parameterization and weakly informative priors on m and τ.
- Calibration: EMOS (a_L, b_L, log s_L) per station ~ N(group mean per lead, τ_L²), fit
  jointly on the stations' hindcast pairs.
- Checks: r-hat < 1.01, no divergences.
- Accept: truncate a long-record station to its last 6 years. Its pooled estimates must sit
  closer to its full-record estimates than the unpooled 6-year fit does, and holdout
  CRPS/Brier must be no worse than unpooled.

### 6.8 Production-Region Index Locations — `regions.py`

The revenue model's national supply shock (`docs/REVENUE_MODEL.md` §5.2) is driven by weather in
the crop's main production regions. Each region is one extra location in the joint simulation:
- Regions: corn and soybeans → `IDX_IA`, `IDX_IL`, `IDX_IN`, `IDX_NE`, `IDX_MN`; HRW wheat →
  `IDX_KS`, `IDX_OK`, `IDX_TXP` (Texas Panhandle), `IDX_NE`. The list lives in config.
- Each index is the daily **average of a few Open-Meteo grid points** (default 4 per region,
  coordinates in config) placed in the region's top-producing areas. A single point is too
  noisy to stand for a region. Season variables are computed from the averaged daily series,
  with the same definitions as everywhere else.
- Index locations go through the same climatology fit, trend switch, and latent-Gaussian
  dependence model as the farm and stations. The correlation matrix covers all L locations.
- The revenue model fits its national-shock regression on the **same** index definitions'
  1995–2024 history, so history and simulation always match.

---

## 7. Output Contract (The Revenue Model and Optimizer Read These; Change Them Together)

Written to `outputs/<run_id>/`. `schema.py` validates every file on write.

**`scenarios_daily.parquet`** — long format
| column | type | notes |
|---|---|---|
| scenario_id | int32 | 0..N−1 |
| date | date | local date |
| location | str | `farm`; station code, 3–5 uppercase alphanumerics (e.g., `ORD`); or index `IDX_<2–3 uppercase>` (e.g., `IDX_IA`) |
| tmax_f | float32 | |
| tmin_f | float32 | tmin ≤ tmax enforced |
| precip_in | float32 | ≥ 0 |

**`scenarios_season.parquet`** — wide, one row per scenario
`scenario_id`, then for each location `<loc>` (farm, stations, and index locations, e.g.
`IDX_IA`): `rain_total_in_<loc>`, `hot_days_95_<loc>`, `gdd_<loc>`.

**`contract_probs.csv`** — one row per candidate contract
| column | notes |
|---|---|
| contract_id | our id, e.g., `ORD_RAIN_JUL_LT_2.5` |
| ticker | Kalshi ticker if known, else empty (filled from `quotes.csv`, see `docs/OPTIMIZER.md` §2) |
| location | station code |
| variable | `rain_total_in`, `hot_days_95`, `gdd`, or daily `tmax_f` / `precip_in` |
| comparator | `lt`, `le`, `gt`, `ge`, `between` |
| threshold | float (and `threshold_hi` for `between`) |
| start, end | date range the contract covers (single day for daily contracts) |
| p_model | fraction of scenarios where contract pays |
| p_se | sqrt(p(1−p)/N) |

Default candidate grid, per selected station and only for the markets that station has:
- `rain`: rain-total thresholds 1.0–7.0 in step 0.5, with both `lt` and `ge`, for **each
  calendar month** in the window (start/end = month bounds).
- `tmax`: daily tmax ≥ 85, 90, 95, 100 for each day in the forecast window.

`payoff_matrix` computes period totals from `daily_df` when a contract's period is not the
full window.

**`run_meta.json`** contains:
- run_id, created_at, forecast issue time, N, seed, window, farm coords, model_version,
  phase reached, calibration scores (Brier/CRPS vs climatology)
- `stations` (list of codes), `locations` (`farm` + stations + index locations)
- crop, `season_window_source`, farm timezone
- `station_info`: per station {code, ghcn_id, name, lat, lon, distance_km, markets,
  record_years, short_record}
- `index_locations`: per index {code, points [[lat, lon], …], distance_km from the farm to
  the index centroid}
- `trend`: {enabled, per location: {tmax_f, tmin_f}: {beta_f_per_decade, se}}
- `basis_risk`: farm–station correlation of season rain, hot days, GDD
- `hedge_diagnostics` (below)

**`hedge_diagnostics`** (in run_meta). For each farm season variable Y (`rain_total_in`,
`hot_days_95`, `gdd` at the farm):
- `max_hedge_effectiveness`: share of Var(Y) explained by the best linear combination of
  all candidate contract payoffs (R² of OLS of Y on the payoff matrix with intercept).
  Measured **out-of-sample**: fit on a random half of scenarios, score on the other half, so
  many correlated contracts can't overstate it.
- `by_station`: the same R² using one station's contracts only.
- `best_single_contract`: {contract_id, r2}.
- `corr_with_station`: {code: farm–station correlation of Y}.
- `distance_km`: {code: km}.

Computed by `hedge.hedge_effectiveness(y, payoffs, rng)`. The optimizer can call the same
function with farm **revenue** scenarios. The weather-variable version in run_meta is a
screening proxy.

### 7.1 Hedge Decision Rule

There is **one** rule: `docs/HEDGE_MODEL.md` §6 (hedge / partial / don't hedge, from the CVaR
improvement and the hedging cost on the evaluation half; thresholds in config). `docs/OPTIMIZER.md`
§7 is the same idea for v2. This repo does not define another. `hedge_diagnostics` feeds its
reasons: a low `max_hedge_effectiveness` or low `corr_with_station` is the evidence for "weak
farm–station link". Educational, not financial advice.

**`payoff_matrix(contracts_df, daily_df, season_df) -> np.ndarray`** in `contracts.py`:
shape (N, n_contracts) of 0/1 payouts. The optimizer (`docs/OPTIMIZER.md` §5.1) imports this.

**`fake.py`**: `make_fake_outputs(N, seed, out_dir)` writes all four files with plausible random
values in exactly this schema, including index locations for the chosen crop, so the revenue
model and optimizer can be built against it.

---

## 8. Validation — `validate/`

- Hold out the last 5 years. Never fit on them.
- Compare three models on holdout: climatology only, raw forecast, calibrated forecast.
- Metrics: Brier score (binary contract events), CRPS (`properscoring.crps_ensemble`) for daily
  tmax and season rain, PIT histogram, reliability diagram (10 bins).
- Climatology sanity: simulated vs historical distributions of season rain total, hot-day count,
  GDD (overlay histograms + compare mean/std; KS test optional).
- Save plots to `outputs/<run_id>/plots/`.

---

## 9. Tests — `tests/`

- `test_schema.py`: fake outputs pass validation; bad outputs (negative rain, tmin > tmax,
  missing columns) fail.
- `test_synthetic.py`: generate synthetic forecasts/obs with known a=−1.5, b=1.0, s=2.5 →
  EMOS MLE recovers them within tolerance. Generate synthetic climate with known p01, p11, k, θ, ρ
  → climatology fit recovers them.
- `test_simulate.py`: with a fixed seed, outputs are reproducible; shapes correct; p_se formula
  correct; simulated p_wet within tolerance of input.
- `test_stations.py`: parse GHCN metadata fixtures; haversine against known distances; nearest-K
  selection respects markets and `--stations` override; auto-lookup resolves ORD/MDW to the
  verified IDs.
- `test_crops.py`: corn → Jul, soybeans → Aug, wheat → Apr–May; `--start/--end` override;
  unknown crop raises.
- `test_synthetic.py` (additions): synthetic temperatures with known separate tmax/tmin trends
  → recovered β within tolerance; with the trend on, σ and τ are not inflated by the trend.
- `test_simulate.py` (additions): index-location daily series = mean of its points;
  `IDX_*` columns present and validated.
- `test_hedge.py`: synthetic Y = linear(payoffs) + noise with known R² → recovered; independent
  payoffs → HE ≈ 0.

Run with `pytest -q`. All tests must pass at the end of every phase.

---

## 10. CLI — `run.py`

```
python run.py --lat 40.1 --lon -88.2 --crop corn|soybeans|wheat [--year 2027] \
  [--start 2027-07-01 --end 2027-07-31] [--stations auto|ORD,MDW] [--k-stations 3] \
  [--trend|--no-trend] --n 10000 --seed 42 \
  [--mode fake|climatology|forecast|hedge] [--issue-date YYYY-MM-DD] [--hierarchical]
```
- `--crop` + farm location set the window from the crop calendar; `--start/--end` override.
- `--stations auto` (default) selects the nearest market stations; a list overrides.
- Every weather run writes its folder path to `outputs/latest_run.txt`; `--mode hedge` reads it.
- `--mode fake`: write fake outputs (Phase 0).
- `--mode climatology`: no forecast.
- `--mode forecast`: full model. `--issue-date` lets us replay a past date using historical
  forecasts (needed for demos/backtests when the window is far away).
Prints a short summary: crop, window, selected stations with distances, key percentiles of
season variables, top contract probabilities, basis-risk correlations, hedge effectiveness,
and the output folder path.

---

## 11. Build Phases (Stop After Each For Review)

**Phase 0 — Skeleton + contract (≈1 h).** Repo structure, requirements, config, `schema.py`,
`fake.py`, `run.py --mode fake`, `test_schema.py`.
Accept: `python run.py --mode fake` writes 4 valid files; `pytest` passes.

**Phase 1 — History + climatology + simulation, one location (≈3 h).** Fetchers for station
history with caching; climatology fit; Markov-chain rain + AR(1) temperature simulator;
aggregation; contract probs; `--mode climatology`.
Accept: simulated vs historical season rain mean/std within ~10%; hot-day distribution similar;
p11 > p01; plots saved.

**Phase 2 — Farm + stations + index locations jointly, nationwide (≈6–8 h).** GHCN station
metadata + automatic ID lookup; market-station list + nearest-K selection with distances;
crop calendar; farm and index-point history (Open-Meteo); production-region index locations;
trend switch; latent-Gaussian dependence model across all locations; basis risk and
hedge_diagnostics in run_meta.
Accept, on **both** reference farms (`champaign_corn`, `salina_wheat`):
- simulated farm–station correlation of season rain and hot days within ~0.1 of historical
- simulated farm–index and index–index correlations of season rain and GDD within ~0.1 of
  historical
- auto-lookup reproduces the verified ORD/MDW IDs
- Phase 1 marginal checks still hold at each location
- trend switch: report holdout (2020–24) bias of season GDD and hot days with the trend on vs
  off, then set the default to whichever is better
- hedge_diagnostics present with HE in [0, 1]

**Phase 3 — Raw ensemble forecast (≈2 h).** Ensemble fetcher (hourly → daily per member);
forecast-window days driven by random members; continuity into climatology days.
Accept: a forecast heat wave raises P(hot days); early-window spread < late-window spread.

**Phase 4 — Calibration, MLE (≈3 h).** Hindcast fetcher; EMOS MLE per lead; rain calibration;
apply to ensemble; `test_synthetic.py` EMOS recovery.
Accept: b ≈ 1, s_L increases with lead; calibrated beats raw on holdout CRPS.

**Phase 5 — Bayesian calibration (≈4–5 h).** PyMC EMOS; posterior draws per scenario; then
the hierarchical pooling option (6.7) for climatology + calibration.
Accept: r-hat < 1.01, no divergences; posterior means ≈ MLE; holdout scores no worse than MLE;
the 6.7 short-record test passes.

**Phase 6 — Validation + backtest (≈2 h).** Full scoring vs climatology/raw/calibrated;
reliability + PIT plots; `--issue-date` replay.
Accept: calibrated model has the best Brier/CRPS; plots ready for the pitch.

If time runs short, a polished Phase 4 is the target; Phases 5–6 are stretch goals.

---

## 12. Honest Limits (Keep in run_meta and README)

- Daily forecast skill fades after ~2 weeks; far-off windows are mostly climatology.
- Contracts settle at city stations; the farm's weather differs (basis risk, reported).
  For many farms (e.g., the Plains) the nearest market station is hundreds of km away;
  hedge_diagnostics quantifies how much that limits any hedge.
- Crop-calendar windows are one national default per crop; actual stage dates shift with region
  and planting date (override with `--start/--end`).
- `hot_days_95` and corn GDD (base 50, cap 86) are corn-oriented. Soybeans and wheat may need
  different stress metrics; adding them is an output-contract change for the revenue model.
- The linear trend is fit on 25 years and extrapolated to the target season; it is a
  simplification of climate change, not a projection.
- The weather model covers weather only; yield and crop prices are in the revenue model.
- Educational tool, not financial advice.

---

## 13. Streamlit App (Build Order Step 4) — `app/streamlit_app.py`

A simple front end over the three modules, run with `.venv/bin/streamlit run app/streamlit_app.py`.
- Inputs: farm location (lat/lon), crop, acres, normal yield, futures price, basis, budget,
  risk weight, max legs.
- Runs: weather model (`--mode climatology`), then the hedge model (`--mode hedge`,
  `docs/HEDGE_MODEL.md` §8), using cached data and params, so a run takes seconds.
- Shows:
  - selected stations with distances
  - the before/after revenue distribution (5th percentile marked) and the natural-hedge %
  - the recommendation (hedge / partial / don't, with its reason)
  - the legs table with entry prices
  - before/after revenue histograms
- Label every unlisted contract "hypothetical" and show "Educational tool, not financial
  advice" on every page. No order placement.
