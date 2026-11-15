# bizfax

A pre-booking carrier screen for small businesses shipping parcels internationally. For each carrier it gives a projected delivery date with an 80% interval, using weather forecasts at the hubs on the route. It recommends the cheapest carrier that is 90% likely to arrive by your deadline.

Demo route: **Germany → Princeton, NJ**. The example customer is a robotics mentor waiting on kits that are only sold in Germany.

## Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
pytest
```

## Layout

| Path | What | Owner |
|---|---|---|
| `bizfax/config.py` | Carriers, hub routes, leg durations, prices (placeholders), disclaimers | A |
| `bizfax/data/weather.py` | Open-Meteo: forecast for the first 7 days, climatology after that, observed weather for replays | A |
| `bizfax/data/bts.py` | BTS on-time data loader → daily hub delay rate | A |
| `bizfax/data/calendar.py` | DE/US holidays, peak season | A |
| `bizfax/model/weather_delay.py` | Weather → P(hub delay). Placeholder coefficients; `fit()` trains them on BTS | B |
| `bizfax/model/simulate.py` | Monte Carlo over route legs plus assumed customs delay | B |
| `bizfax/backtest/olist.py` | Interval backtest on the real Olist data: coverage, pinball loss, comparison with Olist's promised dates | B |
| `bizfax/recommend.py` | Cheapest carrier with P90 ≤ deadline | B |
| `app.py` | Streamlit UI | C |

## Data

| Need | Source | Status |
|---|---|---|
| Backtest | [Olist on Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) → `data/raw/olist/` | download |
| Weather | Open-Meteo (no key needed) | wired |
| US hub delays | [BTS on-time data](https://www.transtats.bts.gov/) CSVs for CVG/SDF/MEM/JFK → `data/raw/bts/` | download |
| EU hub delays | Eurocontrol airport delay data (LEJ/CGN/CDG/FRA) | TODO |
| Real cargo flights | OpenSky REST (≤2-day windows, recent only) | TODO |
| Prices | Shippo live key, quotes only (never buy labels) | TODO — placeholders in config |
| Calendar | `holidays` package | wired |

## Honesty labels (keep on screen)

- Customs delay is an assumed distribution, the same for every carrier.
- Each carrier's shipment history is synthetic.
- The weather→delay coefficients are placeholders until `fit()` runs on BTS data.
