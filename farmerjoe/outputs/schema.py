"""Output contract (CLAUDE.md section 7). DO NOT CHANGE WITHOUT TELLING THE TEAM.

Every file written to outputs/<run_id>/ goes through a validate_*() function here.
Validators raise SchemaError with a readable message on the first problem found.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

DAILY_FILE = "scenarios_daily.parquet"
SEASON_FILE = "scenarios_season.parquet"
CONTRACTS_FILE = "contract_probs.csv"
META_FILE = "run_meta.json"
ALL_FILES = (DAILY_FILE, SEASON_FILE, CONTRACTS_FILE, META_FILE)

DAILY_COLUMNS = ["scenario_id", "date", "location", "tmax_f", "tmin_f", "precip_in"]
DAILY_ARROW_SCHEMA = pa.schema(
    [
        ("scenario_id", pa.int32()),
        ("date", pa.date32()),
        ("location", pa.string()),
        ("tmax_f", pa.float32()),
        ("tmin_f", pa.float32()),
        ("precip_in", pa.float32()),
    ]
)

SEASON_VARS = ("rain_total_in", "hot_days_95", "gdd")
SEASON_DTYPES = {"rain_total_in": np.float32, "hot_days_95": np.int32, "gdd": np.float32}
DAILY_VARS = ("tmax_f", "tmin_f", "precip_in")

CONTRACT_COLUMNS = [
    "contract_id", "ticker", "location", "variable", "comparator",
    "threshold", "threshold_hi", "start", "end", "p_model", "p_se",
]
COMPARATORS = ("lt", "le", "gt", "ge", "between")
CONTRACT_VARIABLES = SEASON_VARS + DAILY_VARS

META_REQUIRED_KEYS = (
    "run_id", "created_at", "forecast_issue_time", "N", "seed", "window", "farm",
    "stations", "model_version", "phase", "calibration_scores", "basis_risk",
)

LOCATION_RE = re.compile(r"^(farm|[A-Z0-9]{3,5}|IDX_[A-Z]{2,3})$")
# Float tolerance for tmin <= tmax and p_se checks.
_EPS = 1e-4


class SchemaError(ValueError):
    """Raised when an output does not match the contract."""


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise SchemaError(msg)


def _require_columns(df: pd.DataFrame, cols: list[str], name: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    _require(not missing, f"{name}: missing columns {missing}")


def _as_dates(s: pd.Series, name: str) -> pd.Series:
    """Coerce a column of date-like values to datetime.date; fail on unparseable values."""
    try:
        out = pd.to_datetime(s, errors="raise")
    except (ValueError, TypeError) as e:
        raise SchemaError(f"{name}: unparseable dates ({e})") from e
    _require(not out.isna().any(), f"{name}: missing dates")
    _require(bool((out == out.dt.normalize()).all()), f"{name}: dates must not carry a time of day")
    return out.dt.date


# ----------------------------------------------------------------------------- daily

def validate_daily(df: pd.DataFrame, n_scenarios: int | None = None) -> pd.DataFrame:
    """Validate scenarios_daily and return a copy cast to contract dtypes.

    Checks: required columns, no NaNs, precip >= 0, tmin <= tmax, location labels,
    scenario ids 0..N-1, and a complete, duplicate-free (scenario, date, location) grid.
    """
    name = "scenarios_daily"
    _require_columns(df, DAILY_COLUMNS, name)
    out = df[DAILY_COLUMNS].copy()
    _require(len(out) > 0, f"{name}: empty")
    _require(not out.isna().any().any(), f"{name}: contains NaN/missing values "
             f"in {out.columns[out.isna().any()].tolist()}")

    sid = out["scenario_id"]
    _require(pd.api.types.is_integer_dtype(sid), f"{name}: scenario_id must be integer")
    out["scenario_id"] = sid.astype(np.int32)
    out["date"] = _as_dates(out["date"], name)
    out["location"] = out["location"].astype(str)
    bad_loc = sorted(l for l in set(out["location"]) if not LOCATION_RE.match(l))
    _require(not bad_loc, f"{name}: invalid location labels {bad_loc} (use 'farm', a station code, or IDX_<region>)")
    for c in DAILY_VARS:
        _require(pd.api.types.is_numeric_dtype(out[c]), f"{name}: {c} must be numeric")
        out[c] = out[c].astype(np.float32)
        _require(bool(np.isfinite(out[c]).all()), f"{name}: {c} has non-finite values")

    _require(bool((out["precip_in"] >= 0).all()), f"{name}: negative precip_in")
    _require(bool((out["tmin_f"] <= out["tmax_f"] + _EPS).all()), f"{name}: tmin_f > tmax_f")

    ids = np.unique(out["scenario_id"].to_numpy())
    n = len(ids) if n_scenarios is None else n_scenarios
    _require(ids.min() == 0 and ids.max() == n - 1 and len(ids) == n,
             f"{name}: scenario_id must cover 0..{n - 1} exactly")
    n_dates, n_locs = out["date"].nunique(), out["location"].nunique()
    _require(len(out) == n * n_dates * n_locs,
             f"{name}: expected full grid {n}x{n_dates}x{n_locs}={n * n_dates * n_locs} rows, got {len(out)}")
    _require(not out.duplicated(["scenario_id", "date", "location"]).any(),
             f"{name}: duplicate (scenario_id, date, location) rows")
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------- season

def season_columns(locations: list[str]) -> list[str]:
    """Column order for scenarios_season."""
    return ["scenario_id"] + [f"{v}_{loc}" for loc in locations for v in SEASON_VARS]


def validate_season(df: pd.DataFrame, locations: list[str] | None = None,
                    n_scenarios: int | None = None) -> pd.DataFrame:
    """Validate scenarios_season (wide, one row per scenario) and cast dtypes.

    If `locations` is None they are inferred from `rain_total_in_<loc>` columns.
    """
    name = "scenarios_season"
    _require("scenario_id" in df.columns, f"{name}: missing columns ['scenario_id']")
    if locations is None:
        locations = [c[len("rain_total_in_"):] for c in df.columns if c.startswith("rain_total_in_")]
        _require(bool(locations), f"{name}: no rain_total_in_<loc> columns")
    cols = season_columns(locations)
    _require_columns(df, cols, name)
    out = df[cols].copy()
    _require(not out.isna().any().any(), f"{name}: contains NaN/missing values")
    _require(pd.api.types.is_integer_dtype(out["scenario_id"]), f"{name}: scenario_id must be integer")
    out["scenario_id"] = out["scenario_id"].astype(np.int32)
    n = len(out) if n_scenarios is None else n_scenarios
    _require(len(out) == n and np.array_equal(np.sort(out["scenario_id"].to_numpy()), np.arange(n)),
             f"{name}: scenario_id must be 0..{n - 1}, one row each")
    for loc in locations:
        for v in SEASON_VARS:
            c = f"{v}_{loc}"
            _require(pd.api.types.is_numeric_dtype(out[c]), f"{name}: {c} must be numeric")
            _require(bool((out[c] >= 0).all()), f"{name}: {c} has negative values")
            if v == "hot_days_95":
                _require(bool((out[c] == np.round(out[c])).all()), f"{name}: {c} must be whole days")
            out[c] = out[c].astype(SEASON_DTYPES[v])
    return out.sort_values("scenario_id").reset_index(drop=True)


# ------------------------------------------------------------------------- contracts

def validate_contracts(df: pd.DataFrame, n_scenarios: int | None = None) -> pd.DataFrame:
    """Validate contract_probs. If n_scenarios is given, check p_se = sqrt(p(1-p)/N)."""
    name = "contract_probs"
    _require_columns(df, CONTRACT_COLUMNS, name)
    out = df[CONTRACT_COLUMNS].copy()
    _require(len(out) > 0, f"{name}: empty")
    _require(out["contract_id"].notna().all() and out["contract_id"].is_unique,
             f"{name}: contract_id must be present and unique")
    out["ticker"] = out["ticker"].astype(object).fillna("").astype(str)  # all-empty CSV column reads as float
    out["location"] = out["location"].astype(str)
    bad_var = sorted(set(out["variable"]) - set(CONTRACT_VARIABLES))
    _require(not bad_var, f"{name}: unknown variables {bad_var}")
    bad_cmp = sorted(set(out["comparator"]) - set(COMPARATORS))
    _require(not bad_cmp, f"{name}: unknown comparators {bad_cmp}")

    for c in ("threshold", "threshold_hi", "p_model", "p_se"):
        out[c] = pd.to_numeric(out[c], errors="coerce").astype(float)
    _require(out["threshold"].notna().all(), f"{name}: threshold missing")
    is_btw = out["comparator"] == "between"
    _require(out.loc[is_btw, "threshold_hi"].notna().all(), f"{name}: 'between' needs threshold_hi")
    _require(bool((out.loc[is_btw, "threshold_hi"] > out.loc[is_btw, "threshold"]).all()),
             f"{name}: threshold_hi must exceed threshold")
    _require(out.loc[~is_btw, "threshold_hi"].isna().all(),
             f"{name}: threshold_hi must be empty unless comparator is 'between'")

    out["start"] = _as_dates(out["start"], f"{name}.start")
    out["end"] = _as_dates(out["end"], f"{name}.end")
    _require(bool((out["start"] <= out["end"]).all()), f"{name}: start after end")

    p, se = out["p_model"], out["p_se"]
    _require(p.notna().all() and bool(((p >= 0) & (p <= 1)).all()), f"{name}: p_model must be in [0, 1]")
    _require(se.notna().all() and bool((se >= 0).all()), f"{name}: p_se must be >= 0")
    if n_scenarios is not None:
        expect = np.sqrt(p * (1 - p) / n_scenarios)
        _require(bool(np.allclose(se, expect, atol=_EPS)), f"{name}: p_se != sqrt(p(1-p)/N)")
    return out.reset_index(drop=True)


# ------------------------------------------------------------------------------ meta

def validate_meta(meta: dict[str, Any]) -> dict[str, Any]:
    """Validate run_meta keys and basic types."""
    name = "run_meta"
    missing = [k for k in META_REQUIRED_KEYS if k not in meta]
    _require(not missing, f"{name}: missing keys {missing}")
    _require(isinstance(meta["N"], int) and meta["N"] > 0, f"{name}: N must be a positive int")
    _require(isinstance(meta["seed"], int), f"{name}: seed must be int")
    w = meta["window"]
    _require(isinstance(w, dict) and {"start", "end"} <= set(w), f"{name}: window needs start/end")
    _require(dt.date.fromisoformat(w["start"]) <= dt.date.fromisoformat(w["end"]),
             f"{name}: window start after end")
    f = meta["farm"]
    _require(isinstance(f, dict) and {"lat", "lon"} <= set(f), f"{name}: farm needs lat/lon")
    _require(-90 <= f["lat"] <= 90 and -180 <= f["lon"] <= 180, f"{name}: farm coords out of range")
    _require(isinstance(meta["stations"], list) and meta["stations"], f"{name}: stations must be a non-empty list")
    _require(isinstance(meta["basis_risk"], dict), f"{name}: basis_risk must be a dict")
    return meta


# ------------------------------------------------------------------------ read/write

def write_daily(df: pd.DataFrame, path: Path, n_scenarios: int | None = None) -> None:
    """Validate and write scenarios_daily.parquet with the exact Arrow schema."""
    out = validate_daily(df, n_scenarios)
    table = pa.Table.from_pandas(out, schema=DAILY_ARROW_SCHEMA, preserve_index=False)
    pq.write_table(table, path)


def write_season(df: pd.DataFrame, path: Path, locations: list[str], n_scenarios: int | None = None) -> None:
    """Validate and write scenarios_season.parquet."""
    validate_season(df, locations, n_scenarios).to_parquet(path, index=False)


def write_contracts(df: pd.DataFrame, path: Path, n_scenarios: int | None = None) -> None:
    """Validate and write contract_probs.csv (dates as ISO strings)."""
    out = validate_contracts(df, n_scenarios)
    out["start"] = out["start"].map(dt.date.isoformat)
    out["end"] = out["end"].map(dt.date.isoformat)
    out.to_csv(path, index=False)


def write_meta(meta: dict[str, Any], path: Path) -> None:
    """Validate and write run_meta.json."""
    Path(path).write_text(json.dumps(validate_meta(meta), indent=2, default=str))


def validate_run_dir(out_dir: str | Path) -> dict[str, Any]:
    """Read back all four files from a run folder and validate them together.

    Returns a small summary dict. Raises SchemaError on any problem, including
    cross-file inconsistencies (N, locations, stations).
    """
    out_dir = Path(out_dir)
    missing = [f for f in ALL_FILES if not (out_dir / f).exists()]
    _require(not missing, f"{out_dir}: missing files {missing}")

    meta = validate_meta(json.loads((out_dir / META_FILE).read_text()))
    n = meta["N"]
    daily_tbl = pq.read_table(out_dir / DAILY_FILE)
    _require(daily_tbl.schema.equals(DAILY_ARROW_SCHEMA, check_metadata=False),
             f"{DAILY_FILE}: arrow schema {daily_tbl.schema} != contract {DAILY_ARROW_SCHEMA}")
    daily = validate_daily(daily_tbl.to_pandas(), n)
    # Phase 1 runs are station-only; from Phase 2 on, locations = farm + stations.
    locations = meta.get("locations", ["farm", *meta["stations"]])
    _require(set(meta["stations"]) <= set(locations), f"{META_FILE}: stations missing from locations")
    _require(set(daily["location"]) == set(locations),
             f"{DAILY_FILE}: locations {sorted(set(daily['location']))} != meta {locations}")
    season = validate_season(pd.read_parquet(out_dir / SEASON_FILE), locations, n)
    contracts = validate_contracts(pd.read_csv(out_dir / CONTRACTS_FILE, keep_default_na=True), n)
    _require(set(contracts["location"]) <= set(locations),
             f"{CONTRACTS_FILE}: contract locations not in run locations")
    return {
        "N": n,
        "daily_rows": len(daily),
        "dates": daily["date"].nunique(),
        "locations": locations,
        "season_columns": len(season.columns),
        "contracts": len(contracts),
    }
