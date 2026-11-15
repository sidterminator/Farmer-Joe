# Farmer Joe frontend

A financial advice app for farmers, in three screens:

1. **Intro.** The name, one promise and a Start button.
2. **Your farm.** The farmer drops a pin on a map (or types a town) and answers six more questions: crop, acres, normal yield, price, budget for hedging, and stability versus cost. The map names every city with a Kalshi weather station.
3. **Advice.** The model suggests which markets to hedge with and how many dollars to put into each. A graph of revenue by harvest shows the farm without the hedge and with it. The farmer can tick hedges, switch sides, change the dollars and review the order.

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

## The model is a placeholder

`advisor.js` is the adviser. `FarmerJoe.advisor.suggest(revenue, markets, { budget, stability })` returns `{ trimmed, picks: [{ id, side, contracts, dollars }] }`: which markets to hedge with, which side, and how much money. The placeholder buys the side that pays in the farm's bad seasons, sizes the mix to be as steady as possible, leans it toward cost by the Priority answer and scales it to the budget. Replace the function with the team's model and keep the return shape.

## How the advice screen behaves

- Ticking or unticking a hedge, or switching it between Yes and No, asks the adviser to size the whole mix again inside the budget.
- Typing or dragging a dollar amount changes only that hedge. Those amounts stand until the next tick or side change, and "Reset" re-sizes on request. Contracts come in hundreds, so a typed amount settles on what it buys.
- Going over the budget shows a warning and a "Trim" action.
- Wording is kept short on purpose: labels and results, no explanations.

## The graph

Harvests run along the bottom and revenue in dollars up the side. One line is the farm without a hedge; the other is the farm with the plan. A rule marks each line's worst harvest.

The 20 harvests are sample seasons from the simulation, not a forecast of particular years. `model.representativeSeasons` picks them so the group stands in for all 20,000: one from each slice of the revenue range, chosen so each market pays out about as often, and in the same kinds of season, as it does overall. On the default farm the 20 match the full simulation's average within about $500 and its swing within about 5%. The table under the graph always shows the full simulation's figures.

## Kalshi

- `kalshi.js` reads open markets from `https://demo-api.kalshi.co/trade-api/v2`, which accepts requests from a web page. The production API refuses requests that carry a browser `Origin`, so live production prices have to come through a server.
- On the demo exchange many markets are listed with nobody quoting them. The panel shows "No offer" for those sides.
- Placing an order needs a signed API key. A web page cannot keep one safe, so `FarmerJoe.source.placeOrders` is a stub and `ordersConnected` is `false`. Wire it to the team's server and set the flag to enable the button.
- `stations.js` lists 38 cities with a Kalshi rain or temperature market (snow-only cities are left out). Each `series` ticker is real, read from Kalshi's series list on 2026-11-14; Great Falls and Orlando exist on production but not on the demo exchange. The `julyHot` and `julyRain` figures are round numbers used only to give the sample markets believable thresholds.
- Kalshi lists monthly markets month by month, so July markets are not open in November. That is why the plan runs on sample July prices and the live panel shows the current month.

## Files

| File | What it does |
|---|---|
| `index.html` | The three screens and the icon sprite |
| `styles.css` | The seed-sack look: layout, colours, states, responsive rules |
| `app.js` | Routing, the farm form, the advice screen, the order, the live panel |
| `map.js` | The map, the Albers projection, the pin and its drop animation |
| `charts.js` | The one chart: revenue by harvest, two lines |
| `advisor.js` | **Placeholder model**: which markets to hedge with and how many dollars in each |
| `model.js` | Hedge maths and the sample-harvest picker (pure functions, no DOM) |
| `sample-data.js` | Sample scenario and the `FarmerJoe.source` seam for the backend |
| `kalshi.js` | Kalshi demo API client |
| `stations.js` | The 38 station cities, and distance helpers |
| `us-map.js`, `places.js` | Generated data: state outlines and 3,355 towns |
| `tools/build-geo.mjs` | Regenerates the two data files; not needed to run the app |
| `fonts/` | Big Shoulders and Archivo (SIL Open Font License), embedded in `fonts.css` so they load from `file://` |

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
    preselect,                     // true if the market starts ticked on the plan
    question,                      // one short line shown on the ticket
    caveat,                        // optional short warning, e.g. "May not exist on Kalshi."
    yesCents, noCents,             // ask prices in cents
    payoutYes: Uint8Array(N)       // 1 where Yes pays, else 0
  }]
}
```

All per-season arrays share one order, so index `s` is one simulated season everywhere. Plain JSON arrays work too.

`source.liveMarkets(station)` resolves to `{ ticker, title, fetchedAt, markets: [{ ticker, label, yesCents, noCents }] }`, or `null` when nothing is open. A side with no offer has `null` cents.

`source.placeOrders([{ market, side, contracts, cents }])` should resolve when the server has accepted the orders.

The frontend computes, per simulated season, `revenue = acres x price x (yield + yieldSd x farmShock) + sum of contracts x (payout - price)`.

## Data credits

- State outlines: [us-atlas](https://github.com/topojson/us-atlas) (ISC licence), from U.S. Census Bureau shapes.
- Town list: [GeoNames](https://www.geonames.org/) (CC BY 4.0).

## Not built yet

- Order placement, fees, bid/ask spread and liquidity limits.
- Alaska and Hawaii on the map.
- A real model for basis risk between the farm and the settlement station.
