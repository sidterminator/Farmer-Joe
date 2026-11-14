# bizfax frontend (v1)

One screen for the weather-hedging tool: a farmer sees their season income with and without a hedge, picks a market and a side, sizes the hedge, saves markets and adds their own seasons.

Plain HTML, CSS and JavaScript. No install and no build step.

## Run

Open `index.html` in a browser. Or serve the folder:

```bash
cd frontend
python3 -m http.server 8000   # then open http://localhost:8000
```

## Everything on screen is sample data

No weather model, market feed or optimizer is connected yet. The farm, the three markets, their prices and the 20,000 simulated seasons are generated in `sample-data.js` from a fixed seed, and the header says so. Uploaded seasons stay in the browser tab; nothing is sent anywhere.

## Files

| File | What it does |
|---|---|
| `index.html` | Page structure and the icon sprite |
| `styles.css` | Layout, colours, states, responsive rules |
| `app.js` | State, rendering, events, CSV and typed-season parsing |
| `charts.js` | The one chart form: a distribution drawn as ribs, with an optional dashed outline |
| `model.js` | Hedge maths (pure functions, no DOM) |
| `sample-data.js` | Sample scenario and the `Bizfax.source` seam for the backend |
| `fonts/` | Public Sans (SIL Open Font License). `public-sans.css` embeds the font so it loads from `file://` |
| `sample/farm-history.csv` | Example file for the Import button |

## Connecting the real models

`app.js` reads data only through `Bizfax.source` in `sample-data.js`. Replace its two functions with `fetch()` calls and keep the shapes below.

`Bizfax.source.scenario()` resolves to:

```js
{
  sample: true,                 // false once the numbers are real; the UI label does not read this yet
  fallbackYieldSd: 20,          // bu/acre, used when a farm has fewer than 3 seasons
  farmShock: Float64Array(N),   // standardised farm-yield shock per simulated season
  farm: { name, crop, acres, pricePerBu, place, seasons: [{ year, yield }] },
  markets: [{
    id, name, question, measure, settles, source, sourceLong,
    unit,                       // 'degF' | 'in' | 'bu/ac'
    strike,                     // number, in `unit`
    yesWhen,                    // 'at-or-above' | 'below'
    yesCents, noCents,          // ask prices in cents
    underlying: Float64Array(N),// the measured value per simulated season
    payoutYes: Uint8Array(N)    // 1 where YES pays, else 0
  }]
}
```

All per-season arrays have the same length and the same order, so index `s` is one simulated season everywhere. Plain JSON arrays work too.

`Bizfax.source.uploadSeasons(seasons)` takes `[{ year, yield }]` and resolves to `{ ok, stored, count }`. When `stored` is false the UI tells the farmer the data stayed in the browser.

The frontend then computes, per simulated season, `income = acres x pricePerBu x (meanYield + sdYield x farmShock) + n x (payout - price)`. `model.js` has the minimum-variance hedge size (`steadiestContracts`) for a single contract.

## Farm data formats

- **Import**: a CSV with a year column and a yield column in bushels per acre. Optional `acres` and `price` columns replace the sample farm's figures. See `sample/farm-history.csv`.
- **Typed**: one season as `year, bushels per acre`, for example `2026, 192`.

Import stages the file; the arrow uploads it.

## Not built yet

- Hedging with more than one market at a time.
- Fees, bid/ask spread, budget cap and liquidity limits.
- Basis risk between the farm and the settlement station.
- Real upload to a server.
