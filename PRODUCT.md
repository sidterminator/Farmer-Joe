# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML/CSS/JS in `frontend/`, no build step and no install (chosen by the user on 2026-11-14). It runs on sample data for now; a small Python API will connect it to the team's models later. The project plan (`info.pdf`) suggested Streamlit; the user chose plain web files because the UI sketch is a custom layout.

## Users

Farmers. The user confirmed the idea is "very specific to farmers". A farmer's income for a season depends on weather they cannot control (heat, rain), and they come to the tool to see which contracts would steady that income.

## Product Purpose

A weather-hedging tool built on prediction-market contracts. It shows the markets that matter to a farm, what each side of a contract costs, and what the farm's income looks like with and without the hedge. Built at HackPrinceton Fall 2026 (Nov 13 to 15, 2026).

## Positioning

It turns a weather forecast into a hedge recommendation for one specific farm: the farm's own data goes in, and the output is which contracts to buy and what they do to the income spread. The plan names the revenue model and the hedge optimizer as the parts that make it a product instead of a forecast.

## Operating Context

- Contracts are binary: each pays $1 or $0, and the price in cents reads as a probability. Every market has a YES side and a NO side.
- Kalshi is the exchange the plan targets. Markets settle on official readings at specific weather stations.
- The farmer supplies their own data: an Import control for files, and a field with a send arrow for uploading data.
- The screen follows the user's sketch (`../UI outline rough draft.png`): a large main panel, a column of market cards with YES and NO prices and a bookmark on each, Import at bottom left, the upload field at bottom right.

## Capabilities and Constraints

- The main panel shows two views: daily income hedged versus unhedged, and forecast versus market price.
- The sketch names two of the three market cards, "Temp" and "Yield". The third is unnamed in the sketch.
- No weather model, market feed or optimizer exists in the repo yet. The frontend runs on sample data and must say so on screen.
- Undecided: what file format farmers upload, what the icon above the upload field in the sketch does, and whether real Kalshi markets exist for crop yield.
- The earlier parcel-carrier code in this repo (`app.py`, `bizfax/`, `tests/`) is a different idea. It stays on disk and is not part of this frontend.

## Brand Commitments

The repo and working name is `bizfax`. No logo, palette or voice has been set.

## Evidence on Hand

- `../info.pdf`: the project plan (weather model, revenue model, market layer, hedge optimizer, backtest, product).
- `../UI outline rough draft.png`: the user's hand-drawn layout.
- No real market prices, forecasts or farm data are in the repo. Nothing shown in the UI may be presented as real until those are wired in.

## Product Principles

1. Label sample and assumed numbers on screen. The repo's README already keeps "honesty labels" visible.
2. The farmer's own income is the subject. Markets are shown in terms of what they do to it.
3. A hedge is insurance, not a bet: the tool sizes the hedge and flags when it is unusually cheap or expensive.
4. Educational tool, not financial advice. The plan requires this disclaimer.
