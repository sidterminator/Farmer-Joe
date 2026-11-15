"""Cached weather runs for the web app and the demo pre-warm (shared by server.py and run.py).

Farm coordinates are snapped to a 0.1-degree grid (about 11 km) before fetching and caching, so
pins near an already-simulated farm reuse its run instead of waiting on fresh downloads.
"""
from __future__ import annotations

import threading
from pathlib import Path

import numpy as np

from farmerjoe.config import load_config

ROOT = Path(__file__).resolve().parent.parent
WEB_RUNS = ROOT / "outputs" / "web"
GRID_DEG = 0.1

_locks: dict[str, threading.Lock] = {}
_guard = threading.Lock()


def snap(lat: float, lon: float) -> tuple[float, float]:
    """Nearest point on the 0.1-degree grid."""
    return round(round(lat / GRID_DEG) * GRID_DEG, 1), round(round(lon / GRID_DEG) * GRID_DEG, 1)


def run_id_for(lat: float, lon: float, crop: str) -> str:
    lat, lon = snap(lat, lon)
    return f"web_{crop}_{lat:.2f}_{lon:.2f}"


def weather_run(lat: float, lon: float, crop: str):
    """(run folder, config) for this farm + crop, building it once if it is not cached."""
    from run import run_joint          # local import: run.py imports this module for --prewarm
    lat, lon = snap(lat, lon)
    run_id = run_id_for(lat, lon, crop)
    out_dir = WEB_RUNS / run_id
    cfg = load_config(overrides={"lat": lat, "lon": lon, "crop": crop, "mode": "climatology",
                                 "output_dir": str(WEB_RUNS)})
    with _guard:
        lock = _locks.setdefault(run_id, threading.Lock())
    with lock:
        if not (out_dir / "run_meta.json").exists():
            run_joint(cfg, out_dir, run_id, np.random.default_rng(cfg.seed), refit=False, skip_validation=True)
    return out_dir, cfg
