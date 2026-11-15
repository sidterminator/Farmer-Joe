# Farmer Joe — Hedge Optimizer Build Spec (Legs, Sizing, Entry Prices)

Read this fully before writing code. Inputs come from the weather model (`CLAUDE.md`) and the
revenue model (`REVENUE_MODEL.md`). Build one phase at a time; after each phase run its acceptance
checks, show results, and stop for review.

---

## 1. Goal

Given the farmer's 10,000-scenario revenue distribution and a universe of yes/no contracts on
**rain, temperature, and crop price**, recommend:

1. **Whether to hedge at all** (hedge / partial / don't hedge, with a one-line reason).
2. **How many legs** (distinct contracts) to use.
3. **Which contracts and which side** (YES or NO) for each leg.
4. **How much to deploy on each leg** (number of contracts and dollars).
5. **An entry price for each leg**: the recommended limit price and the maximum price worth paying.

Markets need not currently exist on Kalshi. Unlisted contracts are priced synthetically and flagged
as hypothetical. This is a recommendation tool; it never places orders.

---

## 2. Inputs

- `scenarios_daily.parquet`, `scenarios_season.parquet`, `contract_probs.csv` (weather model).
- `revenue_scenarios.parquet` (revenue model), same `scenario_id`s.
- User settings: `budget_usd`, `risk_weight` (0 = only care about average, 1 = only care about bad
  years), `max_legs` (default 5), `cvar_alpha` (default 0.05).
- Optional market quotes file `quotes.csv`: contract_id, yes_bid, yes_ask, no_bid, no_ask,
  available_size (contracts), source (`kalshi` | `manual`).

---

## 3. Contract Universe

Every contract pays $1 if its condition is true, else $0. Each can be bought on the **YES** side or
the **NO** side (NO pays when the condition is false).

| Family | Examples | Settles on |
|---|---|---|
| Rain | station season total `lt`/`ge` X in; daily rain yes/no | weather scenarios (station) |
| Temperature | daily high `ge` X°F on a date; count of ≥95°F days `ge` k (hypothetical); season mean `ge` X | weather scenarios (station) |
| Price | crop futures price on settlement date `ge`/`lt` X ¢/bu (ladder of strikes around F) | `harvest_price_usd_bu` |

Generate a grid per family (thresholds spanning the 5th–95th percentile of the simulated variable).
Mark each contract `listed: true/false` from `quotes.csv`.

---

## 4. Prices for Contracts

For contract k with model probability p_k (fraction of scenarios where it pays):
- **Listed:** use the real ask for the side being bought.
- **Unlisted (synthetic quote):** `ask_yes = clip(p_k + half_spread + vig, 0.01, 0.99)`,
  `ask_no = clip((1 − p_k) + half_spread + vig, 0.01, 0.99)`. Defaults: half_spread 0.02, vig 0.01.
  Because synthetic asks sit above fair value, the optimizer buys them only for risk reduction,
  never because they look "cheap." Flag every unlisted leg as hypothetical in outputs.
- **Fees:** configurable function; default approximates Kalshi's taker fee,
  `fee(C, P) = ceil_to_cent(0.07 × C × P × (1 − P))` (verify against current Kalshi docs).

---

## 5. Optimization

### 5.1 Hedged Outcome Per Scenario

For decision variables n_k ≥ 0 (contracts bought on contract-side k at price c_k):

    PL_i = revenue_i + Σ_k n_k · (X_ik − c_k) − fees(n)

X_ik ∈ {0, 1} is the payoff matrix (N × K), built with `payoff_matrix()` from the weather package
plus price contracts evaluated on `harvest_price_usd_bu`.

### 5.2 Objective: Mean–CVaR

Maximize  `(1 − w) · mean(PL) + w · CVaR_α(PL)`, with w = `risk_weight`.
CVaR_α = average of the worst α share of scenarios. Linear-program form (Rockafellar–Uryasev):

    CVaR_α(PL) = max_η  η − (1 / (α N)) · Σ_i max(η − PL_i, 0)

so the whole problem is a linear program with N auxiliary variables (fine for N = 10,000).

### 5.3 Constraints

- Budget: Σ n_k c_k + fees ≤ budget_usd.
- Liquidity: n_k ≤ available_size_k (listed) or a configurable cap (unlisted, default 50,000).
- Legs: binary z_k, n_k ≤ M z_k, Σ z_k ≤ max_legs; minimum leg size n_k ≥ n_min z_k (default 100).
- Integer n_k (or solve the relaxation, round, and re-check feasibility).
- Never hold both YES and NO of the same contract.

Solver: `cvxpy` with HiGHS (MILP) or `scipy.optimize.milp`. Pre-filter candidates to the ~40 with
the strongest payoff correlation with low-revenue scenarios to keep the MILP fast.

### 5.4 Overfitting Guard

Optimize on scenarios 0–4,999; evaluate and report on 5,000–9,999. Reported numbers come from the
evaluation half.

---

## 6. The Three Recommendation Outputs

### 6.1 Number of Legs (Leg Frontier)

Solve with max_legs = 1, 2, …, 5. For each, record objective, CVaR_5, mean, cost.
Recommend the smallest K whose objective is within 5% (configurable) of the best K. More legs only
if they materially help — simpler is better for a farmer.

### 6.2 Deployment Per Leg

For each recommended leg: contract, side, contracts n_k, dollars deployed n_k·c_k + fees, % of
budget, payout if it hits (n_k × $1), probability it pays, and which bad scenarios it covers
(share of the worst-5% scenarios in which it pays).

### 6.3 Entry Price Per Leg

- **Max entry price (reservation price):** the highest price at which the optimizer would still buy
  at least `n_min` contracts of that leg, holding the other legs fixed. Find by bisection on c_k
  (re-solve the LP). Above this price, the leg costs more than the protection is worth.
- **Recommended limit price:** `min(current ask, max entry price)`, rounded down to the cent. If the
  ask exceeds the max entry price, recommend "wait / place limit at max entry price."
- Also report **fair value** (p_k for YES, 1 − p_k for NO) so the farmer sees how much above fair
  value they are paying for protection.

---

## 7. Hedge or Not (Decision Rule, Shared With the Team)

Let ΔCVaR = CVaR_5(hedged) − CVaR_5(unhedged), cost = expected hedging cost = mean(revenue) −
mean(PL) (≥ 0 when paying above fair value), shortfall = mean(revenue) − CVaR_5(unhedged).

- **Hedge:** ΔCVaR ≥ 25% of shortfall AND cost ≤ 2% of mean revenue.
- **Partial hedge:** ΔCVaR ≥ 10% of shortfall AND cost ≤ 4% of mean revenue (then recommend a
  scaled-down version of the best basket).
- **Don't hedge:** otherwise. Reasons (pick the binding one): weak link between farm and contract
  stations (low basis correlation); natural hedge already stabilizes revenue; protection overpriced;
  liquidity too thin for useful size; weather exposure small relative to revenue.
All thresholds live in config.

---

## 8. Strategy Comparison (Demo Feature)

Solve separately with only rain, only temperature, only price, weather (rain+temp), and all
families. Report ΔCVaR, cost, legs for each. Expect price-only to be weak for core Corn Belt farms
(natural hedge) and stronger for peripheral farms — show this as a headline chart.

---

## 9. Outputs

Written to `outputs/<run_id>/hedge/`.
- `recommendation.json`: decision (hedge/partial/none), reason, chosen K, totals (cost, ΔCVaR,
  before/after mean, sd, VaR_5, CVaR_5), hypothetical flag if any leg is unlisted.
- `legs.csv`: one row per leg — contract_id, family, side, condition, settlement, p_model,
  fair_value, ask, max_entry_price, limit_price, contracts, dollars, payout_if_hit, listed.
- `leg_frontier.csv`: K = 1..5 results.
- `strategy_comparison.csv`.
- `plots/`: before/after revenue histograms; leg frontier; strategy comparison bars.

---

## 10. Validation and Tests

- Toy problem with known answer: two-state world (like the "ice cream" example) → optimizer buys the
  exact hedge that equalizes revenue when price = fair value.
- Budget, liquidity, legs and min-size constraints always respected.
- Evaluation-half results reported; train/eval gap shown.
- Same seed → same recommendation.

---

## 11. Build Phases (Stop After Each)

**O0 — Skeleton (≈1 h).** Schemas, fake inputs from teammates' fake files, synthetic quotes, payoff
matrix. Accept: payoff-matrix averages equal p_model.

**O1 — Single-leg min-variance and mean–CVaR LP (≈2 h).** Accept: toy problem solved exactly.

**O2 — Multi-leg MILP with constraints (≈3 h).** Accept: constraints respected; leg frontier produced.

**O3 — Entry prices + hedge-or-not (≈2 h).** Accept: max entry price via bisection; limit prices;
decision with reason.

**O4 — Strategy comparison + plots (≈2 h).** Accept: core vs peripheral farm show the expected
price-only difference.

---

## 12. Conventions

Same as `CLAUDE.md` §3. Educational tool, not financial advice. Never places orders.
