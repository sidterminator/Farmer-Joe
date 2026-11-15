"""Output contract tests: fake outputs validate; broken outputs fail."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from farmerjoe.config import load_config
from farmerjoe.outputs import schema
from farmerjoe.outputs.contracts import contract_probs, payoff_matrix
from farmerjoe.outputs.fake import make_fake_outputs

N = 200


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory) -> Path:
    return make_fake_outputs(N, 7, tmp_path_factory.mktemp("fake"))


@pytest.fixture()
def daily(run_dir) -> pd.DataFrame:
    return pd.read_parquet(run_dir / schema.DAILY_FILE)


@pytest.fixture()
def season(run_dir) -> pd.DataFrame:
    return pd.read_parquet(run_dir / schema.SEASON_FILE)


@pytest.fixture()
def contracts(run_dir) -> pd.DataFrame:
    return pd.read_csv(run_dir / schema.CONTRACTS_FILE)


# --------------------------------------------------------------------------- good path

def test_fake_outputs_validate(run_dir):
    info = schema.validate_run_dir(run_dir)
    assert info["N"] == N
    assert info["locations"] == ["farm", "ORD", "MDW"]
    assert info["daily_rows"] == N * 31 * 3
    # 13 rain thresholds (1.0..7.0) x {lt, ge} + 14 days x 4 tmax thresholds, per station
    assert info["contracts"] == 2 * (13 * 2 + 14 * 4)


def test_daily_arrow_types(run_dir):
    import pyarrow.parquet as pq
    assert pq.read_schema(run_dir / schema.DAILY_FILE).equals(schema.DAILY_ARROW_SCHEMA, check_metadata=False)


def test_season_matches_daily(daily, season):
    farm = daily[daily.location == "ORD"].groupby("scenario_id")["precip_in"].sum()
    np.testing.assert_allclose(season["rain_total_in_ORD"], farm.to_numpy(), rtol=1e-5)
    hot = (daily[daily.location == "farm"].tmax_f >= 95).groupby(daily.scenario_id).sum()
    np.testing.assert_array_equal(season["hot_days_95_farm"], hot.to_numpy())


def test_contract_id_format(contracts):
    assert "ORD_RAIN_JUL_LT_2.5" in set(contracts.contract_id)
    assert "ORD_RAIN_JUL_GE_2.5" in set(contracts.contract_id)
    assert "MDW_TMAX_20270701_GE_95" in set(contracts.contract_id)


def test_payoff_matrix_matches_probs(daily, season, contracts):
    pay = payoff_matrix(contracts, daily, season)
    assert pay.shape == (N, len(contracts))
    assert set(np.unique(pay)) <= {0, 1}
    np.testing.assert_allclose(pay.mean(axis=0), contracts.p_model, atol=1e-12)


def test_rain_probs_monotone(contracts):
    p = contracts[(contracts.location == "ORD") & (contracts.variable == "rain_total_in")
                  & (contracts.comparator == "lt")]
    assert np.all(np.diff(p.sort_values("threshold").p_model) >= 0)


def test_between_comparator(daily, season, contracts):
    c = contracts.iloc[:1].copy()
    c["comparator"], c["threshold"], c["threshold_hi"] = "between", 2.0, 4.0
    x = season["rain_total_in_ORD"]
    got = contract_probs(c, daily, season).p_model.iloc[0]
    assert got == pytest.approx(((x >= 2.0) & (x <= 4.0)).mean())
    schema.validate_contracts(contract_probs(c, daily, season), N)


def test_reproducible(tmp_path):
    a = make_fake_outputs(50, 3, tmp_path / "a")
    b = make_fake_outputs(50, 3, tmp_path / "b")
    pd.testing.assert_frame_equal(pd.read_parquet(a / schema.DAILY_FILE), pd.read_parquet(b / schema.DAILY_FILE))


def test_config_overrides():
    cfg = load_config(overrides={"stations": "chi", "n_scenarios": 5,
                                 "start": "2027-07-03", "end": "2027-07-20"})
    assert cfg.stations == ["CHI"] and cfg.n_scenarios == 5
    assert cfg.season_window_source == "cli" and cfg.start.day == 3
    with pytest.raises(ValueError):
        load_config(overrides={"stations": "XYZ"})


def test_fake_with_index_locations(tmp_path):
    out = make_fake_outputs(30, 1, tmp_path, index_codes=["IDX_IA", "IDX_IL"])
    info = schema.validate_run_dir(out)
    assert "IDX_IA" in info["locations"]
    assert "rain_total_in_IDX_IL" in pd.read_parquet(out / schema.SEASON_FILE).columns


# ---------------------------------------------------------------------------- bad path

def test_negative_rain_fails(daily):
    daily["precip_in"] = daily["precip_in"].astype(float)
    daily.loc[5, "precip_in"] = -0.1
    with pytest.raises(schema.SchemaError, match="negative precip"):
        schema.validate_daily(daily, N)


def test_tmin_above_tmax_fails(daily):
    daily.loc[5, "tmin_f"] = daily.loc[5, "tmax_f"] + 3
    with pytest.raises(schema.SchemaError, match="tmin_f > tmax_f"):
        schema.validate_daily(daily, N)


@pytest.mark.parametrize("col", schema.DAILY_COLUMNS)
def test_missing_daily_column_fails(daily, col):
    with pytest.raises(schema.SchemaError, match="missing columns"):
        schema.validate_daily(daily.drop(columns=col), N)


def test_nan_fails(daily):
    daily.loc[0, "tmax_f"] = np.nan
    with pytest.raises(schema.SchemaError, match="NaN"):
        schema.validate_daily(daily, N)


def test_incomplete_grid_fails(daily):
    with pytest.raises(schema.SchemaError):
        schema.validate_daily(daily.drop(index=10), N)


def test_duplicate_rows_fail(daily):
    bad = daily.copy()
    bad.loc[1, ["date", "location"]] = bad.loc[0, ["date", "location"]].to_numpy()
    with pytest.raises(schema.SchemaError, match="duplicate"):
        schema.validate_daily(bad, N)


def test_bad_location_fails(daily):
    daily["location"] = daily["location"].replace("farm", "Farm Joe")
    with pytest.raises(schema.SchemaError, match="location"):
        schema.validate_daily(daily, N)


def test_missing_season_column_fails(season):
    with pytest.raises(schema.SchemaError, match="missing columns"):
        schema.validate_season(season.drop(columns="gdd_ORD"), ["farm", "ORD", "MDW"], N)


def test_negative_season_rain_fails(season):
    season.loc[0, "rain_total_in_farm"] = -1.0
    with pytest.raises(schema.SchemaError, match="negative"):
        schema.validate_season(season, ["farm", "ORD", "MDW"], N)


def test_bad_contracts_fail(contracts):
    for mutate, msg in [
        (lambda d: d.assign(p_model=1.5), "p_model"),
        (lambda d: d.assign(p_se=d.p_se * 2 + 0.01), "p_se"),
        (lambda d: d.assign(comparator="approx"), "comparators"),
        (lambda d: d.drop(columns="threshold"), "missing columns"),
        (lambda d: d.assign(comparator="between"), "threshold_hi"),
    ]:
        with pytest.raises(schema.SchemaError, match=msg):
            schema.validate_contracts(mutate(contracts.copy()), N)


def test_bad_meta_fails(run_dir):
    meta = json.loads((run_dir / schema.META_FILE).read_text())
    for k in ("run_id", "N", "basis_risk"):
        with pytest.raises(schema.SchemaError, match="missing keys"):
            schema.validate_meta({kk: v for kk, v in meta.items() if kk != k})


def test_missing_file_fails(run_dir, tmp_path):
    for f in schema.ALL_FILES[1:]:
        (tmp_path / f).write_bytes((run_dir / f).read_bytes())
    with pytest.raises(schema.SchemaError, match="missing files"):
        schema.validate_run_dir(tmp_path)


def test_lt_ge_complementary(contracts):
    r = contracts[(contracts.location == "ORD") & (contracts.variable == "rain_total_in")]
    lt = r[r.comparator == "lt"].set_index("threshold").p_model
    ge = r[r.comparator == "ge"].set_index("threshold").p_model
    np.testing.assert_allclose(lt + ge, 1.0, atol=1e-12)
