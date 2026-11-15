"""Interval-forecast evaluation: coverage, width, pinball loss."""
from __future__ import annotations

import numpy as np


def coverage(y: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> float:
    """Share of outcomes inside [lo, hi]. For an 80% interval this should be ~0.80."""
    y, lo, hi = map(np.asarray, (y, lo, hi))
    return float(np.mean((y >= lo) & (y <= hi)))


def mean_width(lo: np.ndarray, hi: np.ndarray) -> float:
    return float(np.mean(np.asarray(hi) - np.asarray(lo)))


def pinball_loss(y: np.ndarray, q_pred: np.ndarray, q: float) -> float:
    """Quantile loss for predicted q-quantile. Lower is better."""
    diff = np.asarray(y) - np.asarray(q_pred)
    return float(np.mean(np.maximum(q * diff, (q - 1) * diff)))
