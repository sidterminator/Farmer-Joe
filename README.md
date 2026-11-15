# Farmer Joe

**Hedge Advice for Farmers, Using Prediction Markets.**

![Farmer Joe Advice Screen](docs/screenshots/advice.png)

A dry July, a heat wave or a price drop can wipe out a farm's year. Farmer Joe simulates 10,000
possible seasons for one specific farm and recommends which weather or crop-price contracts would
protect its income, or says that protection isn't worth buying.

## How It Works

| 1. Describe Your Farm | 2. Get Advice |
|---|---|
| ![Farm Form](docs/screenshots/farm.png) | ![Advice](docs/screenshots/advice.png) |

1. **Describe Your Farm:** location, crop (corn, soybeans or wheat), acres, yield, price, budget.
2. **Simulate the Season:** 30 years of weather history become 10,000 possible seasons.
3. **Get Advice:** the few contracts that best protect your bad years, how many to buy, and the
   most to pay. Or "don't hedge."

## Example

**Dana grows 500 acres of corn near Champaign, Illinois.** A normal year earns her about $414,000;
a bad year (1 in 20), about $267,000. Rain contracts in nearby cities barely track her farm, so
Farmer Joe recommends a **partial hedge**: about $7,500 on "corn price below $3.60," which lifts
her bad-year income by roughly $19,000.

*Illustrative numbers from placeholder settings.*

## Run It

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py --prewarm          # Optional: Cache the Demo Farms
uvicorn server:app --port 8000   # Then Open http://localhost:8000
```

## Limits

Contracts are hypothetical and no orders are placed. Yield and price settings are placeholders.
**Educational tool, not financial advice.**

## Team

Siddharth Tiwari, Lingbo Zhang, Rohan Yadav and Stéphanie Meylan, HackPrinceton Fall 2026.
