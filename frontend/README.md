# Farmer Joe frontend

Three screens for the weather-hedging tool, built for farmers:

1. **Intro.** The name, one promise and a Start button.
2. **Your farm.** The farmer drops a pin on a map (or types a town) and answers seven more questions: crop, acres, normal yield, expected price, what worries them, the most they'll spend, and stability versus cost.
3. **Your plan.** The farmer ticks the markets they want. The amounts are sized together inside the budget, and the graph shows season income without protection and with that combination. They can change the side or the amount on each market and review the order.

Plain HTML, CSS and JavaScript. No install and no build step.

## Run

Open `index.html` in a browser. Or serve the folder:

```bash
cd frontend
python3 -m http.server 8000   # then open http://localhost:8000
```

Screens are addressed by hash: `#/`, `#/farm`, `#/plan`. The farm answers are kept in `sessionStorage` for the visit.

## What is real and what is sample

| Part | Status |
|---|---|
| Map, town list, nearest-station lookup and distance | Real geometry and coordinates (station positions are approximate) |
| "Open on Kalshi now" on the plan screen | **Live**: read from Kalshi's demo exchange in the browser |
| The three July markets, their prices and the model's chances | **Sample**, generated in `sample-data.js` from a fixed seed |
| The 20,000 simulated seasons and the farm's income in each | **Sample** |
| How much distance to the station weakens the hedge | **Sample assumption** (`tracking()` in `sample-data.js`) |
| Sending the order | **Not connected.** The button is disabled and says why |

The screens label sample data. Nothing is sent anywhere except one market-data request to Kalshi's demo API, which carries only a series ticker such as `KXRAININDM`.

## How the plan screen behaves

- Ticking or unticking a market, or switching a market between Yes and No, re-sizes the whole combination inside the budget.
- Typing or dragging an amount changes only that market. Those amounts stand until the next tick or side change, and "Back to the recommended amounts" re-sizes on request.
- The lower band of the graph is labelled with the markets that are in it, for example "With your plan: Temp + Rain".
- Going over the budget shows a warning and a "Trim to fit" action.

## Kalshi

- `kalshi.js` reads open markets from `https://demo-api.kalshi.co/trade-api/v2`, which accepts requests from a web page. The production API refuses requests that carry a browser `Origin`, so live production prices have to come through a server.
- On the demo exchange many markets are listed with nobody quoting them. The panel shows "No offer" for those sides.
- Placing an order needs a signed API key. A web page cannot keep one safe, so `FarmerJoe.source.placeOrders` is a stub and `ordersConnected` is `false`. Wire it to the team's server and set the flag to enable the button.
- `stations.js` lists the stations with a monthly rain series. The series tickers are real (read from Kalshi's series list on 2026-11-14). The `julyHot` and `julyRain` figures are round numbers used only to give the sample markets believable thresholds.
- Kalshi lists monthly markets month by month, so July markets are not open in November. That is why the plan runs on sample July prices and the live panel shows the current month.

## Files

| File | What it does |
|---|---|
| `index.html` | The three screens and the icon sprite |
| `styles.css` | The seed-sack look: layout, colours, states, responsive rules |
| `app.js` | Routing, the farm form, the plan, the order, the live panel |
| `map.js` | The map, the Albers projection, the pin and its drop animation |
| `charts.js` | The one chart form: two distributions on a shared ruled grid |
| `model.js` | Hedge maths (pure functions, no DOM) |
| `sample-data.js` | Sample scenario and the `FarmerJoe.source` seam for the backend |
| `kalshi.js` | Kalshi demo API client |
| `stations.js` | Stations with Kalshi monthly rain markets, and distance helpers |
| `us-map.js`, `places.js` | Generated data: state outlines and 3,355 towns |
| `tools/build-geo.mjs` | Regenerates the two data files; not needed to run the app |
| `fonts/` | Big Shoulders and Archivo (SIL Open Font License), embedded in `fonts.css` so they load from `file://` |
| `sample/farm-history.csv` | Example file for "Import history" on the yield question |

## Connecting the real models

`app.js` reads data only through `FarmerJoe.source` in `sample-data.js`. Replace its functions and keep these shapes.

`source.scenario({ crop, station, miles })` resolves to:

```js
{
  sample: true,
  seasons: N,
  farmShock: Float64Array(N),      // standardised farm-yield shock per simulated season
  tracking: { temperature, rain }, // 0..1, how closely the station's weather follows the farm's
  markets: [{
    id, name,                      // name is the short label on the ticket
    worry,                         // 'heat' | 'drought' | 'crop': which answer pre-selects it
    question, yesPaysWhen, noPaysWhen, settles,
    yesCents, noCents,             // ask prices in cents
    payoutYes: Uint8Array(N)       // 1 where Yes pays, else 0
  }]
}
```

All per-season arrays share one order, so index `s` is one simulated season everywhere. Plain JSON arrays work too.

`source.liveMarkets(station)` resolves to `{ ticker, title, fetchedAt, markets: [{ ticker, label, yesCents, noCents }] }`, or `null` when nothing is open. A side with no offer has `null` cents.

`source.placeOrders([{ market, side, contracts, cents }])` should resolve when the server has accepted the orders.

The frontend computes, per simulated season, `income = acres x price x (yield + yieldSd x farmShock) + sum of contracts x (payout - price)`. `model.recommend` picks the amounts: the steadiest mix for the chosen markets, leaned toward cost by the stability answer, then scaled to fit the budget. It is a stand-in for the team's optimizer.

## Farm history import

A CSV with a year column and a yield column in bushels per acre. It sets the normal yield, and with three or more seasons the swing too. Optional `acres` and `price` columns fill those answers. See `sample/farm-history.csv`.

## Data credits

- State outlines: [us-atlas](https://github.com/topojson/us-atlas) (ISC licence), from U.S. Census Bureau shapes.
- Town list: [GeoNames](https://www.geonames.org/) (CC BY 4.0).

## Not built yet

- Order placement, fees, bid/ask spread and liquidity limits.
- Alaska and Hawaii on the map.
- A real model for basis risk between the farm and the settlement station.
