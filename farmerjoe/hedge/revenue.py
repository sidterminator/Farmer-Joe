"""Revenue per scenario with the natural hedge (HEDGE_MODEL.md §3).

Coefficients are illustrative placeholders from config (`hedge.crops`)."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def yield_dev(rain: np.ndarray, hot: np.ndarray, s: dict[str, Any]) -> np.ndarray:
    """Rule-based fractional yield deviation: too dry, too wet, and heat all cost yield."""
    return (-s["a_rain"] * np.maximum(0.0, s["R_opt"] - rain)
            - s["b_rain"] * np.maximum(0.0, rain - s["R_wet"])
            - s["c_heat"] * hot)


def index_codes(season: pd.DataFrame) -> list[str]:
    return [c[len("rain_total_in_"):] for c in season.columns
            if c.startswith("rain_total_in_IDX_")]


def simulate_revenue(season: pd.DataFrame, s: dict[str, Any], rng: np.random.Generator,
                     rho: float | None = None) -> pd.DataFrame:
    """Per-scenario farm yield, regional yield shock, harvest price and revenue.

    Price: z_p = rho * z_r + sqrt(1 - rho^2) * eps, price = F * exp(sigma * z_p - sigma^2/2),
    with z_r the standardized mean yield deviation over the production-region indexes
    (simulated jointly with the farm, so core-region farms get a stronger natural hedge).
    """
    season = season.sort_values("scenario_id").reset_index(drop=True)
    n = len(season)
    rho = s["rho_price_region"] if rho is None else rho
    farm_dev = yield_dev(season["rain_total_in_farm"].to_numpy(float),
                         season["hot_days_95_farm"].to_numpy(float), s)
    noise = rng.normal(0.0, s["sigma_y"], n)
    farm_yield = s["aph_yield_bu_ac"] * np.maximum(0.0, 1 + farm_dev + noise)

    idx = index_codes(season)
    if not idx:
        raise ValueError("weather run has no production-region index locations (IDX_*)")
    region_dev = np.mean([yield_dev(season[f"rain_total_in_{c}"].to_numpy(float),
                                    season[f"hot_days_95_{c}"].to_numpy(float), s) for c in idx], axis=0)
    sd = region_dev.std()
    z_r = (region_dev - region_dev.mean()) / sd if sd > 0 else np.zeros(n)
    z_p = rho * z_r + np.sqrt(1 - rho**2) * rng.standard_normal(n)
    sig = s["price_vol"]
    price = s["futures_price_usd_bu"] * np.exp(sig * z_p - sig**2 / 2)
    revenue = s["acres"] * farm_yield * np.maximum(price + s["basis_usd_bu"], 0.0)
    return pd.DataFrame({"scenario_id": season["scenario_id"].to_numpy(), "farm_yield_bu_ac": farm_yield,
                         "farm_dev": farm_dev, "region_dev": region_dev, "price_usd_bu": price,
                         "revenue_usd": revenue})


def natural_hedge(rev: pd.DataFrame, s: dict[str, Any], rng: np.random.Generator) -> dict[str, float]:
    """% revenue risk removed by the yield-price link: 1 - sd(actual) / sd(price shuffled)."""
    shuffled = rev["price_usd_bu"].to_numpy()[rng.permutation(len(rev))]
    r_ind = s["acres"] * rev["farm_yield_bu_ac"].to_numpy() * np.maximum(shuffled + s["basis_usd_bu"], 0.0)
    sd_a, sd_i = float(rev["revenue_usd"].std()), float(r_ind.std())
    return {"natural_hedge_pct": 1 - sd_a / sd_i, "sd_actual": sd_a, "sd_independent_price": sd_i,
            "corr_yield_price": float(np.corrcoef(rev["farm_yield_bu_ac"], rev["price_usd_bu"])[0, 1])}
