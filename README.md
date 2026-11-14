# Weather Hedging With Prediction Markets

**Authors:** Siddharth Tiwari, Lingbo Zhang, Rohan Yadav, Stéphanie Meylan

A tool that tells people whose income depends on the weather which prediction market contracts to buy so their daily income becomes as steady as possible, at a cost they are comfortable with.

An ice cream shop loses money on a cold day. A roofer earns nothing when it rains. Weather contracts on Kalshi pay out on exactly those days. This project forecasts the weather as a calibrated probability distribution, models how weather moves a person's revenue, and recommends the mix of contracts that minimizes the variance of their income.

> Educational tool, not financial advice. All order placement uses Kalshi's demo environment. No real money is traded.

## How it works

Data goes in one end and a hedge recommendation comes out the other.

| Part | Question it answers |
| --- | --- |
| 1. Weather model | What will the weather be tomorrow, as a full set of outcomes with probabilities rather than one number? |
| 2. Revenue model | How much money does this person make under each kind of weather? |
| 3. Market layer | Which contracts can they buy, and what do they cost? |
| 4. Hedge optimizer | What mix of contracts makes their daily income as steady as possible? |

## Scope

The first version is deliberately narrow.

- **Personas:** an ice cream shop (sales depend on temperature) and a roofer (a rainy day earns $0). They need two different kinds of weather model.
- **Cities:** only those where Kalshi already lists markets, starting with New York.
- **Contracts:** daily high temperature (series `KXHIGH`) and daily rain (`KXRAIN`).

Farmers and truck drivers are on the roadmap. Farm losses come from season long rain or heat, so they fit monthly markets better than daily ones.

### How the contracts work

- Contracts are binary. Each pays $1 or $0 based on official National Weather Service readings at a specific station.
- The price is a probability. If "NYC high below 70°F" costs 25¢, the market puts that chance at roughly 25%.
- Daily markets are temperature brackets plus "or above" and "or below" levels.
- Settlement stations matter. Chicago temperature markets settle at Midway, but Chicago rain markets settle at O'Hare. The model forecasts the exact station a contract settles on, not the city in general.

## Data

| Type | Source | Use |
| --- | --- | --- |
| Ensemble forecasts | Open-Meteo Ensemble API (free, no key), NWS API at `api.weather.gov` | GFS (about 31 members) and ECMWF (about 51 members) give a raw spread of outcomes |
| Observations | NOAA GHCN-Daily, Open-Meteo historical endpoints | Actual daily highs and rainfall per station |
| Past forecasts | Open-Meteo historical forecast and previous runs endpoints | Measure how wrong forecasts usually are, which the Bayesian layer learns from |
| Market prices | Kalshi public API, demo environment at `external-api.demo.kalshi.co` | Live prices, plus past settled markets for backtesting |

## Weather model: the Bayesian layer

Raw forecast models are biased and overconfident. A model can run 2°F too warm at one airport, and ensemble members usually sit too close together. Treating the raw ensemble as truth gives wrong probabilities and wrong hedges.

- **Prior:** climatology, meaning what is normal for this station on this date.
- **Evidence:** today's ensemble members.
- **Posterior:** a calibrated predictive distribution for tomorrow.

How much weight each side gets is learned from history. Short lead times lean on the forecast, long lead times lean back toward climatology.

**Temperature** uses EMOS (Ensemble Model Output Statistics):

$$T_{\text{high}} \sim \mathcal{N}\left(a + b\,\bar{x}_{\text{ens}},\; c + d\,s^2_{\text{ens}}\right)$$

`a` and `b` correct the bias in the ensemble mean. `c` and `d` correct the overconfidence in the ensemble spread. All four are fit on past forecasts against what actually happened, in PyMC, so the parameters carry their own uncertainty. Bayesian Model Averaging (Raftery et al., 2005) is the fully Bayesian relative and weights GFS and ECMWF by past skill.

**Rain** uses a two part model:

1. Does it rain at all? Logistic regression on the share of ensemble members showing rain.
2. If it rains, how much? A Gamma distribution, which is positive and right skewed like rainfall.

**Calibration checks:** reliability diagram, Brier score, and CRPS, each compared for the raw ensemble against the output of the Bayesian layer.

## Monte Carlo simulation

We draw 10,000 to 100,000 possible tomorrows from the posterior and compute income across all of them.

A single contract on a single day has a closed form answer from the Normal distribution, so no simulation is needed there. Simulation is used for:

- combined events, such as rain on two consecutive days or heat in two cities
- revenue that depends on several variables at once
- optimizing a portfolio of contracts

Weather is correlated across days and cities, so variables are never simulated independently. The simple approach samples whole ensemble members, so each simulated world comes from one internally consistent model run, then adds calibrated noise. The alternative is a Gaussian copula.

A few different seeds are run only as a convergence check. Error shrinks like 1/√N.

## Revenue model

| Persona | Weather driver | Simple model |
| --- | --- | --- |
| Ice cream shop | Temperature (and rain) | Revenue rises with the daily high, then levels off. Rain cuts it by some percentage. |
| Roofer / landscaper | Rain | Rain above about 0.1" means $0 that day. Otherwise the full day rate. |
| Farmer | Season long rain or heat | Losses from drought or heat waves. Better suited to monthly markets. |
| Truck driver | Snow, ice, storms | Delays mean lost loads or penalties. |

Users answer three or four questions (what they make on a great day, on a bad day, and what weather counts as bad) and the revenue function is built from the answers. If a user uploads past daily sales, we fit a regression of sales on weather instead.

## Hedge optimizer

Buy contracts that pay out on exactly the days the business does badly.

### Worked example

An NYC ice cream shop earns $2,000 on a warm day (high of 70°F or more) and $600 on a cold day. The model says P(cold) = 30%. The "below 70°F" contract costs 25¢. Buying 1,400 contracts covers the $1,400 gap and costs $350.

| Outcome | Shop revenue | Contract payout | Cost | Total |
| --- | --- | --- | --- | --- |
| Warm | $2,000 | $0 | −$350 | $1,650 |
| Cold | $600 | $1,400 | −$350 | $1,650 |

Income is locked in with zero variance. Unhedged expected revenue is $1,580, so at 25¢ the hedge also raises the expected result, because the model thinks the contract is underpriced. At a fair 30¢ the average stays at $1,580 with no risk. If the model thinks the price is too high, hedging costs money on average and the user decides whether the stability is worth it.

### General version

For each simulated world `s`:

$$\text{P\&L}_s = R_s + \sum_j n_j \left(X_{sj} - p_j\right)$$

`R` is revenue, `X` is a contract's payout ($1 or $0), `p` is its price, and `n` is how many are bought. Minimizing the variance of hedged P&L gives the minimum variance hedge ratio:

$$n^* = -\,\operatorname{Cov}(X)^{-1}\,\operatorname{Cov}(X, R)$$

In words: buy more of the contracts that move most strongly opposite to revenue, and adjust for contracts that overlap with each other.

On top of that:

- **Risk preference:** maximize (average P&L) − λ × (variance), with a slider for λ from "I just want stability" to "only hedge when it's cheap".
- **Constraints:** whole numbers of contracts, a budget cap, Kalshi's trading fees, and the bid/ask spread. The user pays the ask, not the midpoint.
- **Liquidity:** never recommend more contracts than are realistically available near the listed price.
- **Multi leg positions:** adjacent temperature brackets combine into custom payout shapes, for example more contracts in colder brackets when losses grow as it gets colder.

### Basis risk

The client's shop is not at the airport where the contract settles, and markets exist in only about 20 cities. We measure this by comparing historical weather at the client's location with the settlement station, and report it as "this hedge removes about X% of your weather risk".

## Backtest

The full pipeline runs on past days using only the information available at the time: the forecasts made that day and the market prices from that day. The optimizer picks the hedge, and it settles against what actually happened.

Reported metrics:

- standard deviation of daily income, unhedged vs. hedged (the headline number)
- worst day, unhedged vs. hedged
- average cost of hedging per day
- model vs. market calibration, compared against Kalshi's published accuracy and Brier score statistics for its daily weather markets

The main thing to guard against is look ahead bias, meaning any use of information from after the forecast time.

## Product

Built in Streamlit, with the whole stack in Python: pandas, NumPy, SciPy, PyMC.

User flow:

1. Pick a persona.
2. Pick a city.
3. Answer the revenue questions.
4. See tomorrow's weather distribution.
5. Get the recommended contracts.
6. See a before and after chart of their income spread.

The key chart is two overlapping histograms of daily income: a wide one for unhedged and a narrow one for hedged.

## Roadmap

1. Prove the pipeline: one city (NYC), one market (daily high), raw ensemble to probability, compared against the Kalshi price.
2. Add the Bayesian calibration layer, fit on history, with the reliability plot.
3. Build the revenue model and the two outcome hedge.
4. Add Monte Carlo and the minimum variance optimizer for multi contract hedges.
5. Add rain and the roofer persona.
6. Backtest and build the UI.
7. Prepare the demo story.

## Known pitfalls

- **Time zones and daily cutoffs:** the "daily high" follows the NWS definition of a day, which runs on local standard time and is off by an hour during daylight saving. Each contract's settlement rules must be read.
- **Fees and spreads:** small edges in the model's favor can disappear once these are paid.
- **The hedger does not need to beat the market:** a roofer hedging rain is buying insurance. The model's job is to size the hedge correctly and to flag when a hedge is unusually cheap or expensive.

## References

- Kalshi Help: Weather Markets
- Kalshi Research: Hedging Climate Risk
- Kalshi API Docs
- Open-Meteo Ensemble and Historical Forecast APIs
- NOAA GHCN-Daily
- Raftery, Gneiting, Balabdaoui, Polakowski (2005), Using Bayesian Model Averaging to Calibrate Forecast Ensembles
