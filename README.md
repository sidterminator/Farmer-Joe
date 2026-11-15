# Farmer Joe

**Weather and price protection advice for farmers, in plain numbers.**

A farmer's income depends on things they can't control: a dry July, a heat wave, or a drop in
crop prices. Farmer Joe looks at one specific farm, imagines thousands of possible seasons, and
recommends which prediction-market contracts would steady that farm's income — or tells the
farmer that protection isn't worth buying.

Built at HackPrinceton Fall 2026.

---

## How It Works (In Four Steps)

1. **Tell us about your farm.** Drop a pin on the map, pick a crop (corn, soybeans, or wheat), and
   enter your acres, normal yield, expected price, and how much you'd spend on protection.
2. **We learn your weather.** We pull 30 years of real weather history for your farm, the nearest
   cities with weather markets, and the country's main growing regions.
3. **We imagine 10,000 seasons.** The computer plays out the coming season 10,000 different ways —
   droughts, washouts, heat waves, and everything in between — and works out your income in each.
4. **We recommend a hedge, or none.** We test simple yes/no contracts on rain, heat, and crop
   price, pick the few that best protect your bad years, and tell you how many to buy and the most
   you should pay for each.

---

## Example (Made-Up Farm)

> **Dana grows 500 acres of corn near Champaign, Illinois.** In a normal year she earns about
> $414,000. In a bad year (1 in 20), she earns about $267,000 or less.
>
> Farmer Joe notices something useful: when the whole Corn Belt has a bad season, corn prices tend
> to rise, which already cushions part of Dana's loss. Her location gives her a built-in partial
> hedge.
>
> It also finds that weather contracts in Indianapolis and Chicago, 105 and 129 miles away, barely
> track Dana's farm, so they wouldn't protect her much. A **"corn price below $3.60" contract**
> protects her best.
>
> **Recommendation: partial hedge.** Spend about $7,500 on that contract (28,800 contracts at
> 26¢). Her bad-year income rises by roughly $20,000, for an expected cost of about $800.

*These numbers come from our model with placeholder settings. They are an illustration, not
financial advice.*

---

## What We Found

- **Where you farm changes the right hedge.** Farms in the heart of the Corn Belt get a natural
  cushion, because a bad regional harvest pushes prices up. Farms outside it don't.
- **City weather markets help rural farms less than you'd expect.** Contracts settle on weather at
  big-city airports, which can be very different from weather 100+ miles away.
- **Sometimes the best advice is "don't hedge."** If protection costs too much for what it saves,
  Farmer Joe says so.

---

## Run It

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --port 8000
```

Then open **http://localhost:8000**. The first time you ask about a new farm, the server downloads
its weather history and builds the simulation (about 20–90 seconds); after that it answers in
under a second. The website also opens straight from `frontend/index.html` on sample data if the
server isn't running.

---

## What's in the Repo

| Folder | What it is |
|---|---|
| `frontend/` | The website: farm form, map, advice screen, revenue chart |
| `farmerjoe/` | The model: weather simulation, farm income, hedge finder |
| `server.py` | Connects the website to the model |
| `tests/` | Checks that the model behaves correctly |
| `docs/` | Design notes and future ideas |

---

## Honest Limits

- Contracts are **hypothetical**: they are modeled on Kalshi's yes/no markets, but many don't
  exist today. Nothing places real orders.
- Crop yields and prices use **placeholder settings**, not fitted to real farm data yet.
- Weather is based on 1995–2019 history (a warming-trend option exists but is off), not on this
  week's forecast.
- **Educational tool, not financial advice.**

---

## Team

Built at HackPrinceton Fall 2026 by Siddharth Tiwari, Lingbo Zhang, Rohan Yadav, and Stéphanie
Meylan. Licensed under the terms in `LICENSE`.
