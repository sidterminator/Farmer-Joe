"""Production-region index locations (CLAUDE.md 6.8)."""
from __future__ import annotations

from typing import Any

import numpy as np

from farmerjoe.stations import haversine_km


def index_locations(regions: dict[str, list[list[float]]], farm_lat: float, farm_lon: float) -> list[dict[str, Any]]:
    """[{code, points, centroid, distance_km}] for the crop's regions, in config order."""
    out = []
    for code, pts in regions.items():
        arr = np.asarray(pts, dtype=float)
        c = arr.mean(axis=0)
        out.append({"code": code, "points": arr.tolist(), "centroid": [round(float(c[0]), 3), round(float(c[1]), 3)],
                    "distance_km": round(float(haversine_km(farm_lat, farm_lon, c[0], c[1])), 1)})
    return out
