import datetime as dt

import pytest

from farmerjoe.config import load_config
from farmerjoe.crops import default_year, season_window

TABLE = {"corn": {"start_month": 7, "end_month": 7}, "soybeans": {"start_month": 8, "end_month": 8},
         "wheat": {"start_month": 4, "end_month": 5}}


@pytest.mark.parametrize("crop,start,end", [("corn", (7, 1), (7, 31)), ("soybeans", (8, 1), (8, 31)),
                                            ("wheat", (4, 1), (5, 31))])
def test_windows(crop, start, end):
    s, e = season_window(crop, 2027, TABLE)
    assert (s.month, s.day) == start and (e.month, e.day) == end


def test_default_year_is_next_unstarted_season():
    assert default_year("corn", TABLE, dt.date(2026, 11, 14)) == 2027
    assert default_year("corn", TABLE, dt.date(2027, 3, 1)) == 2027
    assert default_year("wheat", TABLE, dt.date(2027, 4, 2)) == 2028


def test_unknown_crop_raises():
    with pytest.raises(ValueError, match="valid crops"):
        season_window("cotton", 2027, TABLE)


def test_config_uses_calendar_and_cli_override():
    cfg = load_config(overrides={"farm": "salina_wheat", "year": 2027})
    assert (cfg.start, cfg.end, cfg.season_window_source) == (dt.date(2027, 4, 1), dt.date(2027, 5, 31), "crop_calendar")
    assert set(cfg.regions) == {"IDX_KS", "IDX_OK", "IDX_TXP", "IDX_NE"}
    cfg = load_config(overrides={"farm": "salina_wheat", "start": "2027-05-01", "end": "2027-06-30"})
    assert cfg.season_window_source == "cli" and cfg.end.month == 6
    cfg = load_config(overrides={"lat": 41.0, "lon": -95.0, "crop": "soybeans", "year": 2027})
    assert cfg.farm_name is None and cfg.start == dt.date(2027, 8, 1)
