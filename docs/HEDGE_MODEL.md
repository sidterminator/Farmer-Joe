# Farmer Joe — Simple Hedge Model Spec (v1)

Read this fully before writing code. This is the **simple** version of the second model. It
replaces build-order steps 2–3 (REVENUE_MODEL R0–R4, OPTIMIZER O0–O3) for now; those two specs
remain as "v2" ideas. Build one phase at a time, run its checks, show results, stop for review.

No Kalshi scraping. Contracts are generated from our own scenarios and priced synthetically.
Output is a recommendation, never an order.

---

## 1. What It Does (In One Paragraph)

Read the latest weather run (10,000 scenarios). For each scenario compute the farmer's revenue
(yield from weather × price, with the natural hedge). Build a menu of simple yes/no contracts on
rain, temperature, and crop price. Find the best hedge: **which contracts (1–3 legs), which side,
how many contracts, how many dollars, and the max entry price for each** — or recommend not
hedging. Save the hedged and unhedged revenue distributions.

---

## 2. Inputs

- `outputs/latest_run.txt` → weather run folder: `scenarios_season.parquet`, `run_meta.json`.
- Farmer settings (config + CLI + dashboard): `crop`, `acres`, `aph_yield_bu_ac`,
  `futures_price_usd_bu`, `price_vol` (annualized-to-harvest vol), `basis_usd_bu` (default 0),
  `budget_usd`, `risk_weight` w ∈ [0, 1] (default 0.7), `max_legs` (default 3).
- Defaults per crop live in `config.yaml` under `hedge:` and are **illustrative placeholders —
  update before demo**: corn $4.50, vol 0.25; soybeans $11.00, vol 0.20; wheat $5.75, vol 0.28.

---

## 3. Revenue Per Scenario (Simple, With Natural Hedge)

### 3.1 Yield From Weather (Rule-Based)

    yield_dev = − a_rain · max(0, R_opt − R) − b_rain · max(0, R − R_wet)
                − c_heat · H − (small GDD term optional)
    farm_yield = aph_yield × max(0, 1 + yield_dev + noise),   noise ~ Normal(0, σ_y)

R = season rain at the farm, H = hot days ≥ 95°F at the farm. Coefficients per crop in config,
**illustrative placeholders** (document as such), e.g. corn: R_opt 4.0 in, R_wet 8.0 in,
a_rain 0.06/in, b_rain 0.03/in, c_heat 0.03/day, σ_y 0.05. Soybeans and wheat similar, with the
wheat window from the crop calendar.

### 3.2 Price With the Natural Hedge

Compute the same yield rule on the **production-region index** locations (average their
yield_dev → `region_dev` per scenario). Standardize: z_r = (region_dev − mean) / sd.

    z_p = ρ · z_r + sqrt(1 − ρ²) · ε,     ε ~ Normal(0, 1)
    price = F · exp(σ · z_p − σ²/2)        (lognormal; mean ≈ F)

ρ = corr(price shock, region yield) is **negative** (bad regional harvest → higher price).
Defaults (config, illustrative): corn −0.5, soybeans −0.4, wheat −0.3. Because the farm and the
regions are simulated jointly, core-region farms automatically get a stronger natural hedge.

### 3.3 Revenue

`revenue = acres × farm_yield × max(price + basis, 0)`.

Natural-hedge diagnostic: recompute revenue with the price column shuffled (independent price),
report `% revenue-risk reduced by natural hedge = 1 − sd(actual) / sd(shuffled)`.

---

## 4. Contract Menu (Season-Level Only, Keep It Small)

Each pays $1 if true, else $0; each may be bought YES or NO.
- Rain: station season rain `lt` X for X at the 10th, 20th, 30th, 40th percentiles of simulated
  station rain (drought protection), and `ge` X at the 70th, 80th, 90th (flood protection).
- Heat: station hot days ≥ 95°F `ge` k for k at the 60th, 75th, 90th percentiles (k ≥ 1).
- Price: harvest price `lt` K and `ge` K for K = F × {0.80, 0.90, 1.10, 1.20}.
Stations: those selected by the weather model (nearest market stations).

**Synthetic price** for a side with model probability p (fraction of scenarios where it pays):
`ask = min(0.99, p + 0.03)` (configurable markup). Flag all as `hypothetical: true`.

---

## 5. Finding the Hedge (Simple Greedy Search)

Hedged outcome for scenario i: `PL_i = revenue_i + Σ_legs n · (payout_i − ask)`.

Score to maximize: `score = (1 − w) · mean(PL) + w · CVaR_5(PL)`,
where CVaR_5 = average of the worst 5% of scenarios.

Use scenarios 0–4,999 to choose; report results on 5,000–9,999 (avoids overfitting).

1. **Best single leg.** For every contract-side, try sizes n on a grid from 0 to budget/ask
   (e.g., 40 steps, round to 100 contracts). Keep the (contract, n) with the best score.
2. **Add legs greedily** up to `max_legs`: add the contract-side that most improves the score
   (re-size the new leg on the grid with others fixed, then one pass re-sizing every leg). Stop if
   the score improves by less than 2% of the gain achieved so far.
3. Respect budget (Σ n · ask ≤ budget) and never hold YES and NO of the same contract.

### Entry Price Per Leg

- **Max entry price:** highest ask at which that leg still gets n ≥ 100 when re-sized with other
  legs fixed (bisection on the ask, ~12 iterations).
- **Recommended limit price:** min(synthetic ask, max entry price), rounded down to the cent.
- Also show **fair value** (p for YES, 1 − p for NO).

---

## 6. Hedge or Not (Same Rule Everywhere)

ΔCVaR = CVaR_5(hedged) − CVaR_5(unhedged); cost = mean(revenue) − mean(PL);
shortfall = mean(revenue) − CVaR_5(unhedged). All on the evaluation half.
- **Hedge:** ΔCVaR ≥ 25% of shortfall and cost ≤ 2% of mean revenue.
- **Partial:** ΔCVaR ≥ 10% of shortfall and cost ≤ 4% of mean revenue (scale legs down by half).
- **Don't hedge:** otherwise. Give the binding reason: weak farm–station link, natural hedge
  already strong, protection too expensive, or exposure small. Thresholds in config.

---

## 7. Outputs — `outputs/<run_id>/hedge/`

- `revenue_scenarios.parquet`: scenario_id, farm_yield_bu_ac, region_dev, price_usd_bu,
  revenue_usd, hedged_pl_usd.
- `recommendation.json`: decision, reason, totals (cost, ΔCVaR, before/after mean, sd, 5th
  percentile, CVaR_5), natural-hedge %, hypothetical flag, all settings used.
- `legs.csv`: contract_id, family, station or crop, side, condition, p_model, fair_value, ask,
  max_entry_price, limit_price, contracts, dollars, payout_if_hit.
- `plots/`: before/after revenue histograms (one chart, two colors, 5th percentile marked).

Command: `python run.py --mode hedge [--budget 15000 --risk-weight 0.7 ...]` (uses latest run).

---

## 8. Dashboard (Extend `app/weather_dashboard.py`, Keep It Clean)

Add a second section below the weather distribution: farmer inputs (acres, yield, futures price,
budget, risk slider) → "Find hedge" button → show the decision + reason in one line, the
before/after revenue histogram, and the legs table. Nothing else. Footer: "Educational tool, not
financial advice. Contracts are hypothetical."

---

## 9. Tests

- Two-state toy problem: optimizer buys the exact hedge that equalizes revenue when ask = fair value.
- Budget respected; no YES+NO of the same contract; same seed → same result.
- Natural-hedge check: with ρ = −0.5, the core farm (central Illinois corn) shows a positive
  natural-hedge %; setting ρ = 0 makes it ≈ 0.

---

## 10. Phases (Stop After Each)

**H0 (≈1 h):** config defaults, revenue per scenario, natural-hedge diagnostic, revenue histogram.
**H1 (≈1.5 h):** contract menu, synthetic prices, payoff table, single-leg search, toy test.
**H2 (≈1.5 h):** multi-leg greedy, entry prices, hedge-or-not, outputs, `--mode hedge`.
**H3 (≈1 h):** dashboard section. Demo on all three test farms; show the decisions side by side.
