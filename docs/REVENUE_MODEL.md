# Farmer Joe — Revenue Model Build Spec (Yield × Price, With the Natural Hedge)

Read this fully before writing code. It plugs into the weather model described in `CLAUDE.md`
and feeds the hedge optimizer described in `OPTIMIZER.md`. Build one phase at a time; after each
phase run its acceptance checks, show results (numbers + plots), and stop for review.

---

## 1. Goal

For a farm (location, crop, acres, normal yield), produce the **distribution of the farmer's
revenue** across the same 10,000 scenarios the weather model generates. Revenue is

    revenue_i = acres × farm_yield_i × (harvest_price_i + basis)

where `farm_yield_i` comes from that scenario's weather and `harvest_price_i` is simulated
**jointly** with weather so the **natural hedge** is captured: when the main growing region has a
bad season, national supply falls and price rises, partly offsetting the farmer's lost bushels.

Crops in scope: **corn, soybeans, wheat** (hard red winter wheat for the Plains; config allows soft
red winter). Every scenario row keeps its `scenario_id` from the weather model — never reshuffle.

---

## 2. Why the Natural Hedge Matters (Design Driver)

- In the core Corn Belt, farm yields and prices are strongly negatively correlated (roughly −0.3
  to −0.7 for corn by area). Revenue is therefore less risky than yield × price treated separately.
- The strength depends on **location**: core-region farms move national supply; peripheral farms
  (e.g., the Southeast) don't, so their price risk is unhedged and their revenue risk is higher.
- Consequence for hedging: price-floor contracts are weak hedges for core-region farms (they pay in
  big-harvest years when the farm is fine) and stronger hedges for peripheral farms. The model must
  reproduce this, and the optimizer must see it through the joint scenarios.

---

## 3. Inputs

From the user (config / CLI):
- `crop` ∈ {corn, soybeans, wheat}; farm `lat`, `lon`; `acres`.
- `aph_yield_bu_ac` (the farm's normal yield). Default: detrended county average from NASS.
- `basis_usd_bu` (local cash price minus futures). Default 0 with a warning.
- Optional `revenue_protection`: {coverage_level, enabled} (simplified USDA RP; stretch phase).

From the weather model (scenario files, see `CLAUDE.md` §7):
- Farm season variables per scenario: `rain_total_in_farm`, `hot_days_95_farm`, `gdd_farm`.
- **Production-region index variables per scenario** (new interface requirement, §9).

From data (cache to `data/raw/`, verify endpoints against live docs):
- **USDA NASS Quick Stats API** (free API key): county and national yields, 1995–2024, for each crop.
- **USDA RMA price discovery**: each year's projected price (pre-season futures average) and harvest
  price (harvest-time futures average), plus the projected-price **volatility factor**, per crop.
  These give, per year, the market's starting price, the realized harvest price, and the market's
  implied volatility.
- **Current futures price and implied volatility** for the coming season: user input or a public
  quote source; fallback to the latest RMA projected price and volatility factor.

---

## 4. Crop Calendar (Defaults; Configurable)

| Crop | Critical weather window | Harvest price window (settlement) |
|---|---|---|
| Corn | July (pollination) | October |
| Soybeans | August (pod fill) | October |
| Wheat (HRW) | April–May (heading, grain fill) | July |

The weather model's season window is set from this table. Price contracts for a crop settle on a
date inside its harvest window.

---

## 5. Model Specification

### 5.1 Farm Yield Model (Weather → Yield)

Fit on county-level NASS yields joined to county weather history (same variables and definitions as
the weather model), per crop, over counties in the farm's region:

1. **Detrend** each county's yield with a linear (or quadratic) time trend: technology raises yields
   every year. Work with percent deviation from trend: `dev = yield / trend − 1`.
2. **Regress** deviation on season weather, allowing curvature (too little and too much rain both
   hurt): `dev ~ rain + rain² + hot_days + gdd (+ gdd²)`.
3. **Bayesian hierarchical version (PyMC):** county coefficients partially pooled toward regional
   means, so counties with short records borrow strength. Priors weakly informative (hot_days
   coefficient expected ≤ 0).
4. Residual yield noise (pests, hail, management) ~ Normal(0, σ_county) — keep it; it is real risk.

Per scenario: `farm_yield_i = aph_yield × (1 + dev_hat(weather_i) + noise_i)`, floored at 0.

### 5.2 National Supply Shock

Per crop, model detrended **national** yield deviation as a function of production-region weather:
`nat_dev ~ Σ_r w_r · f(weather index in region r) + ε_nat`, fit on 1995–2024.
Regions: corn/soy → Iowa, Illinois, Indiana, Nebraska, Minnesota; HRW wheat → Kansas, Oklahoma,
Texas Panhandle, Nebraska. Per scenario, compute `nat_dev_i` from that scenario's simulated
region indices plus a draw of ε_nat.

Because the farm and the regions are simulated jointly by the weather model, a core-region farm's
weather is strongly tied to `nat_dev_i` and a peripheral farm's weakly. **The natural hedge emerges
from geography automatically; do not hard-code a correlation.**

### 5.3 Harvest Price Model (Lognormal, Linked to Supply)

    log(P_i / F) = γ · nat_dev_i + σ_res · z_i − ½·Var(total log-return)
    z_i ~ Normal(0, 1)

- `F` = current futures price for the harvest-window contract (market's expected harvest price).
  The drift term makes E[P_i] ≈ F.
- `γ` (< 0): price sensitivity to national supply. Fit from history: regress
  log(harvest price / projected price) on `nat_dev` by year (RMA prices + NASS national yields).
  Bayesian version in PyMC with prior γ ~ Normal(−2, 1.5) (adjust after looking at data).
- `σ_res` set so total log-return volatility matches the market's implied volatility σ_mkt:
  `σ_res = sqrt(max(σ_mkt² − γ²·Var(nat_dev), floor²))`. Log and report if the floor binds.
- Lognormal because prices stay positive and have a right tail.

### 5.4 Revenue

`revenue_i = acres × farm_yield_i × max(P_i + basis, 0)`.
Optional (stretch): add a simplified RP insurance indemnity:
guarantee = coverage × aph_yield × max(projected price, harvest price) × acres;
indemnity = max(guarantee − acres × farm_yield × harvest price, 0); subtract premium (config).

---

## 6. Outputs (Contract With the Optimizer)

Written to `outputs/<run_id>/revenue/`.

**`revenue_scenarios.parquet`** — one row per scenario
| column | notes |
|---|---|
| scenario_id | same ids as the weather model |
| farm_yield_bu_ac | |
| yield_dev | percent deviation from APH |
| nat_dev | national supply shock |
| harvest_price_usd_bu | futures-equivalent price at settlement |
| revenue_usd | without insurance |
| revenue_usd_insured | if RP enabled, else equal to revenue_usd |

**`revenue_distribution.json`** — the distribution summary
- mean, sd, percentiles (1, 5, 10, 25, 50, 75, 90, 95, 99)
- VaR_5 (5th percentile) and **CVaR_5** (average of the worst 5% of scenarios)
- P(revenue < x) for x = 50%, 70%, 90% of expected revenue
- histogram bins + counts (for plotting by the frontend)

**`natural_hedge.json`** — diagnostics
- corr(farm_yield, price) across scenarios
- revenue sd actual vs revenue sd if price were drawn independently of weather (re-pair the same
  draws with a shuffled price column) → `% risk reduced by natural hedge`
- variance decomposition: share of revenue variance from yield, from price, and from their covariance

**Plots** (`plots/`): revenue histogram with VaR/CVaR marked; yield vs price scatter; the
natural-hedge comparison (actual vs independent).

---

## 7. Validation

- Yield model: holdout last 5 years by county; report RMSE vs a trend-only baseline. Must beat it.
- Price model: simulated distribution of log(harvest/projected) vs history; simulated γ recovered.
- **Natural-hedge check:** simulated farm price–yield correlation for a core Corn Belt county
  (e.g., central Illinois corn) should be clearly negative (roughly −0.3 to −0.7); for a peripheral
  county (e.g., eastern North Carolina corn) it should be much weaker. Report both.
- Revenue: simulated revenue sd for the core county is lower than the "independent" counterfactual.

---

## 8. Build Phases (Stop After Each)

**R0 — Skeleton + fake outputs (≈1 h).** Schema, `make_fake_revenue_outputs()` using the weather
model's fake scenarios; teammates unblocked. Accept: valid files; tests pass.

**R1 — Data (≈2 h).** NASS county/national yields, RMA projected/harvest prices + volatility
factors, cached. Accept: 30 years per crop present; plots of national yield trend and price ratios.

**R2 — Yield model, MLE (≈2–3 h).** Detrend + weather regression per crop. Accept: beats trend-only
on holdout; hot-day coefficient negative for corn; rain effect concave.

**R3 — National shock + price model (≈2–3 h).** Accept: γ < 0 and significant for corn/soy; total
simulated price vol ≈ σ_mkt; E[P] ≈ F within 1%.

**R4 — Joint revenue + natural-hedge diagnostics (≈2 h).** Accept: §7 natural-hedge check passes for
the core vs peripheral pair; distribution files written.

**R5 — Bayesian versions (stretch, ≈3 h).** Hierarchical yield model and Bayesian γ; posterior draws
used per scenario. Accept: r-hat < 1.01; holdout no worse.

**R6 — RP insurance option (stretch).**

---

## 9. Interface Requirements for the Weather Model (Add to CLAUDE.md Work)

1. Simulate **production-region index locations** for the chosen crop (list in §5.2) jointly with
   the farm and stations, using the same latent-Gaussian dependence model. Write their season
   variables to `scenarios_season.parquet` with location codes like `IDX_IA`, `IDX_KS`.
2. Season window comes from the crop calendar (§4).
3. Keep `scenario_id` aligned across all files.

---

## 10. Conventions

Same as `CLAUDE.md` §3 (single rng passed down, vectorized, cached downloads, `.venv`, pytest).
Units: bushels, USD per bushel, USD. Educational tool, not financial advice.
