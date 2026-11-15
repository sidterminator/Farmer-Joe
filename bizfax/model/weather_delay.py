"""Weather -> probability that a hub departure is delayed that day.

DEFAULT_COEFS are hand-set placeholders. Person B: replace with `fit()` on
BTS (US hubs) / Eurocontrol (EU hubs) daily delay rates joined to observed weather.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURES = ("precip", "snow", "wind_excess", "frost")

# logit(p) = intercept + sum(coef * feature)   -- PLACEHOLDER VALUES
DEFAULT_COEFS = {"intercept": -3.0, "precip": 0.08, "snow": 0.9, "wind_excess": 0.06, "frost": 0.05}


def features(weather: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "precip": weather["precipitation_sum"].fillna(0),
        "snow": weather["snowfall_sum"].fillna(0),
        "wind_excess": (weather["wind_speed_10m_max"].fillna(0) - 35).clip(lower=0),
        "frost": (-weather["temperature_2m_min"].fillna(5)).clip(lower=0),
    }, index=weather.index)


def delay_probability(weather: pd.DataFrame, coefs: dict | None = None) -> pd.Series:
    c = coefs or DEFAULT_COEFS
    X = features(weather)
    logit = c["intercept"] + sum(c[f] * X[f] for f in FEATURES)
    return pd.Series(1 / (1 + np.exp(-logit)), index=weather.index, name="p_delay")


def fit(weather: pd.DataFrame, delay_rate: pd.Series, weights: pd.Series | None = None) -> dict:
    """Fit coefficients on daily delay rates (fractional-response logistic regression).

    `weather` and `delay_rate` must share an index (airport-day rows).
    """
    from sklearn.linear_model import LogisticRegression

    X = features(weather).to_numpy()
    y = delay_rate.to_numpy()
    w = np.ones(len(y)) if weights is None else weights.to_numpy()
    # Expand each day into a positive and a negative row weighted by the rate.
    Xx = np.vstack([X, X])
    yy = np.r_[np.ones(len(y)), np.zeros(len(y))]
    ww = np.r_[w * y, w * (1 - y)]
    m = LogisticRegression(C=10.0, max_iter=1000).fit(Xx, yy, sample_weight=ww)
    return {"intercept": float(m.intercept_[0]), **{f: float(v) for f, v in zip(FEATURES, m.coef_[0])}}
