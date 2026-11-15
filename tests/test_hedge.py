import numpy as np
import pytest

from farmerjoe.outputs.hedge import hedge_effectiveness


def test_recovers_known_r2():
    rng = np.random.default_rng(0)
    n = 20_000
    X = (rng.random((n, 3)) < [0.3, 0.5, 0.2]).astype(float)
    signal = X @ np.array([2.0, -1.0, 1.5])
    noise_sd = signal.std()  # -> true R^2 = 0.5
    y = signal + rng.normal(0, noise_sd, n)
    assert hedge_effectiveness(y, X, np.random.default_rng(1)) == pytest.approx(0.5, abs=0.02)


def test_independent_payoffs_near_zero():
    rng = np.random.default_rng(2)
    y = rng.normal(size=10_000)
    X = (rng.random((10_000, 40)) < 0.4).astype(float)
    assert hedge_effectiveness(y, X, np.random.default_rng(3)) < 0.01


def test_degenerate_returns_none():
    assert hedge_effectiveness(np.ones(100), np.random.default_rng(0).random((100, 2)),
                               np.random.default_rng(0)) is None
