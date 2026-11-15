import datetime as dt

import numpy as np
import pandas as pd

from bizfax.backtest.metrics import coverage, pinball_loss
from bizfax.config import CARRIERS
from bizfax.model.simulate import simulate_carrier, summarize
from bizfax.model.weather_delay import delay_probability
from bizfax.recommend import recommend

SHIP = dt.date(2026, 11, 16)  # a Monday


def test_coverage_and_pinball():
    y = np.array([1, 2, 3, 4, 5])
    assert coverage(y, np.full(5, 2), np.full(5, 4)) == 0.6
    assert pinball_loss(y, y, 0.9) == 0.0
    # under-predicting a high quantile costs more than over-predicting
    assert pinball_loss(y, y - 1, 0.9) > pinball_loss(y, y + 1, 0.9)


def test_simulation_is_deterministic_and_ordered():
    c = CARRIERS[0]
    a = simulate_carrier(c, SHIP, {}, n=2000, seed=1)
    b = simulate_carrier(c, SHIP, {}, n=2000, seed=1)
    assert np.array_equal(a, b)
    s = summarize(a, SHIP, SHIP + dt.timedelta(days=7))
    assert s["p10"] <= s["p50"] <= s["p90"]
    assert 0 <= s["p_on_time"] <= 1


def test_bad_weather_delays_arrival():
    c = CARRIERS[0]
    node = next(l.weather_node for l in c.legs if l.weather_node)
    stormy = pd.Series({SHIP + dt.timedelta(days=i): 0.9 for i in range(30)})
    calm = simulate_carrier(c, SHIP, {}, n=5000, seed=2)
    storm = simulate_carrier(c, SHIP, {node: stormy}, n=5000, seed=2)
    assert np.median(storm) > np.median(calm)


def test_delay_probability_rises_with_snow():
    w = pd.DataFrame({"precipitation_sum": [0, 0], "snowfall_sum": [0, 10],
                      "wind_speed_10m_max": [10, 10], "temperature_2m_min": [5, 5]})
    p = delay_probability(w)
    assert p.iloc[1] > p.iloc[0]


def test_recommend_picks_cheapest_that_makes_deadline():
    d = dt.date(2026, 11, 22)
    rows = [
        {"carrier": "Fast", "price_usd": 200, "p50": dt.date(2026, 11, 18), "p90": dt.date(2026, 11, 19)},
        {"carrier": "Cheap", "price_usd": 50, "p50": dt.date(2026, 11, 21), "p90": dt.date(2026, 11, 26)},
        {"carrier": "Mid", "price_usd": 120, "p50": dt.date(2026, 11, 19), "p90": dt.date(2026, 11, 21)},
    ]
    assert recommend(rows, d)["pick"]["carrier"] == "Mid"
    assert recommend(rows, dt.date(2026, 11, 17))["pick"] is None
