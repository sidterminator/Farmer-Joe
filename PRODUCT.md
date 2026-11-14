# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML/CSS/JS in `frontend/`, no build step and no install (chosen by the user on 2026-11-14). It must open straight from disk. The team README describes a Streamlit product; the user chose plain web files for the frontend because the screens are custom layouts.

## Users

Farmers. The user confirmed the idea is "very specific to farmers". A farmer's income for a season depends on weather they cannot control (heat, drought), and they come to the tool to see which contracts would steady that income and what the protection costs.

The team README on `main` lists an ice cream shop and a roofer as the first personas, with farmers on the roadmap. The frontend follows the user's direction and is built for farmers.

## Product Purpose

Farmer Joe is a weather-hedging tool built on prediction-market contracts. The farmer describes their farm, and the tool shows which contracts to buy, how many, what they cost, and what the farm's season income looks like with and without them. Built at HackPrinceton Fall 2026 (Nov 13 to 15, 2026). Repo: `sidterminator/Farmer-Joe` (renamed from `bizfax`).

## Positioning

It turns a weather forecast into a hedge recommendation for one specific farm: the farm's own details go in, and the output is which contracts to buy and what they do to the income spread. The plan names the revenue model and the hedge optimizer as the parts that make it a product instead of a forecast.

## Operating Context

Three screens, in order (user's spec, 2026-11-14):

1. **Intro.** The Farmer Joe name and text, with a Start button.
2. **Farm form.** The questions from `../input form.png`: where the farm is, crop, acres, normal yield, expected price, what worries you, the most you'll spend on protection, and a stability-versus-cost slider. Entering the location drops a pin on a map with an animation. Controls are interactive buttons and sliders.
3. **Results and advice.** The recommended contracts, with the farmer choosing which ones and how many, using the Kalshi API.

Market facts:

- Contracts are binary: each pays $1 or $0, and the price in cents reads as a probability. Every market has a Yes side and a No side.
- Kalshi is the exchange. Markets settle on official readings at specific weather stations, so the tool works from the station nearest the farm.
- Kalshi lists monthly rain markets for many cities (for example series `KXRAINCHIM`, Chicago) and daily high-temperature markets. Monthly markets are listed month by month, so July markets are not open in November.
- Kalshi's demo API (`demo-api.kalshi.co`) answers market-data requests from a browser. The production API refuses requests that carry a browser `Origin`. Placing orders needs a signed API key, which a web page cannot hold safely, so orders must go through the team's server.
- All order placement uses Kalshi's demo environment. No real money is traded.

## Capabilities and Constraints

- No weather model, optimizer or order server is connected yet. Forecasts, the July markets and their prices are sample data, and the screen must say so.
- The live part today is reading currently open markets from the Kalshi demo API for the station nearest the farm.
- Undecided: which real markets map to a farm's July heat and drought risk, how distance to the settlement station reduces the hedge (the frontend uses a labelled sample assumption), and whether a market for crop yield exists.
- The earlier parcel-carrier code in this repo (`app.py`, `bizfax/`, `tests/`) is a different idea. It stays on disk and is not part of this frontend.

## Brand Commitments

- The name is **Farmer Joe**. It is the product's name only, not a character the app speaks as (user, 2026-11-14).
- Visual direction chosen by the user on 2026-11-14: **seed sack**. It replaced the earlier blue and corn gold look.
- Palette set by the user on 2026-11-14: **green and white with red highlights**. The corn yellow the seed sack look first shipped with was removed.

## Evidence on Hand

- `../info.pdf`: the project plan.
- `../UI outline rough draft.png`: the user's first layout sketch (market cards with Yes and No prices and a marker on each).
- `../input form.png`: the form questions with one worked example (Dana: near Champaign, IL; corn; 300 acres; 200 bushels per acre; $4.50 per bushel; heat and drought in July; $15,000; "mostly stability").
- State outlines from us-atlas and a town list from GeoNames are bundled in `frontend/`.
- No real forecasts, July prices or farm records are in the repo. Nothing shown may be presented as real unless it came from the Kalshi API in that session.

## Product Principles

1. Label sample and assumed numbers on screen, and say which numbers are live.
2. The farmer's own income is the subject. Contracts are shown in terms of what they do to it.
3. A hedge is insurance, not a bet: the tool sizes the hedge, respects the farmer's budget, and flags when a contract is unusually cheap or expensive.
4. Never trade real money, and never ask for an API key in the browser.
5. Educational tool, not financial advice. The plan requires this disclaimer.
