"""Load config.yaml and apply CLI overrides."""
from __future__ import annotations

import copy
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from farmerjoe.crops import default_year, season_window

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
VALID_MODES = ("fake", "climatology", "forecast", "hedge")


@dataclass
class Config:
    """Resolved run configuration."""

    farm_name: str | None
    lat: float
    lon: float
    crop: str
    year: int
    start: dt.date
    end: dt.date
    season_window_source: str           # "crop_calendar" | "cli"
    stations: str | list[str]           # "auto" or explicit codes
    k_stations: int
    max_station_km: float
    market_stations: dict[str, dict[str, Any]]
    regions: dict[str, list[list[float]]]   # index code -> points, for this crop
    crop_calendar: dict[str, Any]
    n_scenarios: int
    seed: int
    mode: str
    issue_date: dt.date | None
    forecast_horizon_days: int
    output_dir: Path
    data_dir: Path
    contracts: dict[str, Any]
    history: dict[str, Any] = field(default_factory=dict)
    climatology: dict[str, Any] = field(default_factory=dict)

    @property
    def dates(self) -> list[dt.date]:
        """All local dates in the season window, inclusive."""
        n = (self.end - self.start).days + 1
        return [self.start + dt.timedelta(days=i) for i in range(n)]

    @property
    def fit_years(self) -> tuple[int, int]:
        """Training years: history minus the most recent holdout years (never fit on these)."""
        h = self.history
        return int(h.get("start_year", 1995)), int(h.get("end_year", 2024)) - int(h.get("holdout_years", 5))

    @property
    def holdout_years(self) -> tuple[int, int]:
        h = self.history
        end = int(h.get("end_year", 2024))
        return end - int(h.get("holdout_years", 5)) + 1, end

    @property
    def all_years(self) -> tuple[int, int]:
        return self.fit_years[0], self.holdout_years[1]


def _to_date(x: Any) -> dt.date | None:
    if x is None or isinstance(x, dt.date):
        return x
    return dt.date.fromisoformat(str(x))


def load_config(path: str | Path | None = None, overrides: dict[str, Any] | None = None,
                today: dt.date | None = None) -> Config:
    """Read YAML config and apply non-None overrides.

    Override keys: farm, lat, lon, crop, year, start, end, stations, k_stations, n_scenarios,
    seed, mode, issue_date, output_dir, trend.
    Precedence for the farm: --lat/--lon/--crop > --farm > config `farm`.
    """
    raw = copy.deepcopy(yaml.safe_load(Path(path or DEFAULT_CONFIG_PATH).read_text()))
    ov = {k: v for k, v in (overrides or {}).items() if v is not None}

    farm_name = ov.get("farm", raw.get("farm"))
    farms = raw.get("farms", {})
    if farm_name is not None and farm_name not in farms:
        raise ValueError(f"unknown farm {farm_name!r}; known farms: {sorted(farms)}")
    base = farms.get(farm_name, {})
    lat, lon, crop = ov.get("lat", base.get("lat")), ov.get("lon", base.get("lon")), ov.get("crop", base.get("crop"))
    if lat is None or lon is None or crop is None:
        raise ValueError("need a farm: --farm <name> or --lat, --lon and --crop")
    if any(k in ov for k in ("lat", "lon")):
        farm_name = None  # custom location, not a named reference farm

    table = raw["crop_calendar"]
    year = int(ov.get("year", raw.get("year") or default_year(crop, table, today)))
    start, end = _to_date(ov.get("start")), _to_date(ov.get("end"))
    if (start is None) != (end is None):
        raise ValueError("--start and --end must be given together")
    if start is None:
        start, end = season_window(crop, year, table)
        source = "crop_calendar"
    else:
        source, year = "cli", start.year

    stations = ov.get("stations", raw.get("stations", "auto"))
    if isinstance(stations, str) and stations.lower() != "auto":
        stations = [s.strip().upper() for s in stations.split(",") if s.strip()]
    elif isinstance(stations, str):
        stations = "auto"

    clim = dict(raw.get("climatology", {}))
    if "trend" in ov:
        clim["trend"] = bool(ov["trend"])

    regions_all = raw.get("regions", {})
    cfg = Config(
        farm_name=farm_name, lat=float(lat), lon=float(lon), crop=str(crop), year=year,
        start=start, end=end, season_window_source=source,
        stations=stations, k_stations=int(ov.get("k_stations", raw.get("k_stations", 3))),
        max_station_km=float(raw.get("max_station_km", 400)),
        market_stations=_market_stations(raw, Path(path or DEFAULT_CONFIG_PATH)),
        regions=dict(regions_all.get(crop, {})),
        crop_calendar=table,
        n_scenarios=int(ov.get("n_scenarios", raw["n_scenarios"])),
        seed=int(ov.get("seed", raw["seed"])),
        mode=str(ov.get("mode", raw["mode"])),
        issue_date=_to_date(ov.get("issue_date", raw.get("issue_date"))),
        forecast_horizon_days=int(raw.get("forecast_horizon_days", 14)),
        output_dir=Path(ov.get("output_dir", raw.get("output_dir", "outputs"))),
        data_dir=Path(raw.get("data_dir", "data")),
        contracts=dict(raw.get("contracts", {})),
        history=dict(raw.get("history", {})),
        climatology=clim,
    )
    _check(cfg)
    return cfg


def _market_stations(raw: dict, cfg_path: Path) -> dict[str, dict[str, Any]]:
    """Market stations from `market_stations_file` (frontend/stations.js) or an inline map."""
    f = raw.get("market_stations_file")
    if f:
        from farmerjoe.stations import load_market_stations_js
        p = Path(f)
        return load_market_stations_js(p if p.is_absolute() else cfg_path.parent / p)
    return dict(raw.get("market_stations", {}))


def _check(cfg: Config) -> None:
    if cfg.mode not in VALID_MODES:
        raise ValueError(f"mode must be one of {VALID_MODES}, got {cfg.mode!r}")
    if cfg.end < cfg.start:
        raise ValueError(f"window end {cfg.end} is before start {cfg.start}")
    if cfg.start.year != cfg.end.year:
        raise ValueError("season window may not cross Dec 31")
    if cfg.n_scenarios < 1:
        raise ValueError("n_scenarios must be >= 1")
    if not (-90 <= cfg.lat <= 90 and -180 <= cfg.lon <= 180):
        raise ValueError("farm coordinates out of range")
    if cfg.stations != "auto":
        if not cfg.stations:
            raise ValueError("at least one settlement station is required")
        unknown = [s for s in cfg.stations if s not in cfg.market_stations]
        if unknown:
            raise ValueError(f"stations not in market_stations: {unknown}")
    if cfg.k_stations < 1:
        raise ValueError("k_stations must be >= 1")
    if not cfg.regions:
        raise ValueError(f"no production regions configured for crop {cfg.crop!r}")
