"""GHCN-Daily station list + inventory from NCEI (cached in data/raw as parquet, US only)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

BASE = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/"
# Fixed-width layouts from NCEI's GHCN-Daily readme (1-based inclusive columns -> 0-based).
STATION_COLS = [(0, 11), (12, 20), (21, 30), (31, 37), (38, 40), (41, 71)]
STATION_NAMES = ["id", "lat", "lon", "elev_m", "state", "name"]
INVENTORY_COLS = [(0, 11), (12, 20), (21, 30), (31, 35), (36, 40), (41, 45)]
INVENTORY_NAMES = ["id", "lat", "lon", "element", "first_year", "last_year"]


def _download(name: str, raw_dir: Path) -> Path:
    path = raw_dir / name
    if not path.exists():
        resp = requests.get(BASE + name, timeout=600)
        resp.raise_for_status()
        path.write_bytes(resp.content)
    return path


def parse_stations(path: str | Path) -> pd.DataFrame:
    df = pd.read_fwf(path, colspecs=STATION_COLS, names=STATION_NAMES, dtype={"id": str, "state": str})
    df["name"] = df["name"].fillna("").str.strip()
    return df


def parse_inventory(path: str | Path) -> pd.DataFrame:
    return pd.read_fwf(path, colspecs=INVENTORY_COLS, names=INVENTORY_NAMES, dtype={"id": str})


def load_station_meta(raw_dir: str | Path = "data/raw") -> tuple[pd.DataFrame, pd.DataFrame]:
    """(stations, inventory) for US stations (IDs starting 'US'), cached as parquet."""
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    st_pq, inv_pq = raw_dir / "ghcnd_stations_us.parquet", raw_dir / "ghcnd_inventory_us.parquet"
    if not (st_pq.exists() and inv_pq.exists()):
        st = parse_stations(_download("ghcnd-stations.txt", raw_dir))
        inv = parse_inventory(_download("ghcnd-inventory.txt", raw_dir))
        st[st["id"].str.startswith("US")].to_parquet(st_pq, index=False)
        inv[inv["id"].str.startswith("US")].to_parquet(inv_pq, index=False)
    return pd.read_parquet(st_pq), pd.read_parquet(inv_pq)
