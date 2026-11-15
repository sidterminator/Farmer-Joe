"""Pre-download data and pre-build the weather runs for the demo farms, so the demo never
waits on downloads. Safe to re-run (everything is cached under data/ and outputs/web/).

    .venv/bin/python prefetch_demo.py
"""
import time

import server

# Coordinates exactly as the frontend's town picker sends them (frontend/places.js),
# plus the reference farms from config.yaml.
DEMO_FARMS = [
    ("Champaign, IL", 40.12, -88.24, "corn"),
    ("Salina, KS", 38.84, -97.61, "wheat"),
    ("Kinston, NC", 35.26, -77.58, "corn"),
    ("champaign_corn (reference)", 40.10, -88.20, "corn"),
    ("salina_wheat (reference)", 38.80, -97.60, "wheat"),
    ("enc_corn (reference)", 35.40, -77.60, "corn"),
]

if __name__ == "__main__":
    for name, lat, lon, crop in DEMO_FARMS:
        t = time.perf_counter()
        out_dir, _ = server.weather_run(lat, lon, crop)
        print(f"{name:28s} {crop:6s} ready in {time.perf_counter() - t:5.1f}s  -> {out_dir}", flush=True)
