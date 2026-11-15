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

Farmer Joe is a financial advice app for farmers (the user's positioning, 2026-11-14). The farmer describes their farm, and the app's model suggests which weather markets to hedge with and how many dollars to put into each. A graph of revenue by harvest shows the farm without the hedge beside the farm with it. Built at HackPrinceton Fall 2026 (Nov 13 to 15, 2026). Repo: `sidterminator/Farmer-Joe` (renamed from `bizfax`).

## Positioning

It turns a weather forecast into a hedge recommendation for one specific farm: the farm's own details go in, and the output is which contracts to buy and what they do to the income spread. The plan names the revenue model and the hedge optimizer as the parts that make it a product instead of a forecast.

## Operating Context

Three screens, in order (user's spec, 2026-11-14):

1. **Intro.** The Farmer Joe name and text, with a Start button.
2. **Farm form.** Farm location, crop, acres, normal yield, price, budget for hedging, and a stability-versus-cost slider. Setting the location drops a pin on a map with an animation. The map names every city that has a Kalshi weather station. The questions began from `../input form.png`; on 2026-11-14 the user removed the "what worries you" question and the yield-history import, removed the red place stamp under the town, and renamed the spend question "Budget for hedging".
3. **Advice.** The model's suggestion in dollars per hedge, a graph with harvests along the bottom and revenue in dollars up the side (one line without the hedge, one with), and the hedges themselves, where the farmer chooses which ones and how much.

Market facts:

- Contracts are binary: each pays $1 or $0, and the price in cents reads as a probability. Every market has a Yes side and a No side.
- Kalshi is the exchange. Markets settle on official readings at specific weather stations, so the tool works from the station nearest the farm.
- Kalshi lists monthly rain markets for many cities (for example series `KXRAINCHIM`, Chicago) and daily high-temperature markets. Monthly markets are listed month by month, so July markets are not open in November.
- Kalshi's demo API (`demo-api.kalshi.co`) answers market-data requests from a browser. The production API refuses requests that carry a browser `Origin`. Placing orders needs a signed API key, which a web page cannot hold safely, so orders must go through the team's server.
- All order placement uses Kalshi's demo environment. No real money is traded.

## Capabilities and Constraints

- The adviser is a placeholder model (`frontend/advisor.js`) until the team's model replaces it. No weather model or order server is connected yet. Forecasts, the July markets and their prices are sample data, and the screen must say so.
- The live part today is reading currently open markets from the Kalshi demo API for the station nearest the farm.
- Undecided: which real markets map to a farm's July heat and drought risk, how distance to the settlement station reduces the hedge (the sample ignores it), and whether a market for crop yield exists.
- The earlier parcel-carrier code in this repo (`app.py`, `bizfax/`, `tests/`) is a different idea. It stays on disk and is not part of this frontend.

## Brand Commitments

- The name is **Farmer Joe**. It is the product's name only, not a character the app speaks as (user, 2026-11-14).
- Visual direction chosen by the user on 2026-11-14: **seed sack**. It replaced the earlier blue and corn gold look.
- Palette set by the user on 2026-11-14: **green and white**, with red kept for the pin, stamps, No and warnings. The user went back and forth with a yellow version the same day and settled here. The Start button is white with a plain black arrow (no circle).
- Copy: keep wording short. The user asked for only the important information on every screen.
- The plan's graph overlays the two income shapes on one plot.

## Demo data

On 2026-11-14 the user asked for the sample data to be exaggerated "a lot" so the graph shows a large gap between hedging and not. The sample world in `frontend/sample-data.js` is therefore far kinder to the hedge than a real one: fixed large losses in hot or dry Julys, no distance effect, and contracts priced about 28 points below the model's chance. Its figures (for example 71% less swing and +$21,100 per average harvest on the default farm) are an illustration and must not be quoted as a result.

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
5. The app presents itself as financial advice (user, 2026-11-14), so the "not financial advice" line was removed from the screens. The team's plan and the README on `main` still carry that disclaimer; settle which one stands before anything real is traded. Sample-data labels stay either way.
