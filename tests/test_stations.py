import warnings

import numpy as np
import pandas as pd
import pytest

from farmerjoe.fetch.station_meta import parse_inventory, parse_stations
from farmerjoe.stations import find_ghcn_candidates, haversine_km, select_stations

STATIONS_TXT = """\
USW00014819  41.7842  -87.7553  185.9 IL CHICAGO MIDWAY AP                      72534
USC00111577  41.7372  -87.7775  189.0 IL CHICAGO MIDWAY 3 SW
USW00094846  41.9603  -87.9317  204.8 IL CHICAGO OHARE INTL AP                  72530
"""
INVENTORY_TXT = """\
USW00014819  41.7842  -87.7553 TMAX 1997 2026
USW00014819  41.7842  -87.7553 TMIN 1997 2026
USW00014819  41.7842  -87.7553 PRCP 1998 2026
USC00111577  41.7372  -87.7775 TMAX 1928 2026
USC00111577  41.7372  -87.7775 TMIN 1928 2026
USC00111577  41.7372  -87.7775 PRCP 1928 2026
USW00094846  41.9603  -87.9317 TMAX 1958 2026
USW00094846  41.9603  -87.9317 PRCP 1958 2026
"""


@pytest.fixture()
def meta(tmp_path):
    (tmp_path / "s.txt").write_text(STATIONS_TXT)
    (tmp_path / "i.txt").write_text(INVENTORY_TXT)
    return parse_stations(tmp_path / "s.txt"), parse_inventory(tmp_path / "i.txt")


def test_parse(meta):
    st, inv = meta
    assert list(st.id) == ["USW00014819", "USC00111577", "USW00094846"]
    assert st.loc[0, "name"] == "CHICAGO MIDWAY AP" and st.loc[0, "state"] == "IL"
    assert inv.loc[0, "element"] == "TMAX" and inv.loc[2, "first_year"] == 1998


def test_haversine_known():
    # ORD -> MDW about 24 km; Chicago -> NYC about 1,150 km
    assert haversine_km(41.9603, -87.9317, 41.7842, -87.7553) == pytest.approx(24.2, abs=0.5)
    assert haversine_km(41.88, -87.63, 40.71, -74.01) == pytest.approx(1145, rel=0.01)


def test_candidates_prefer_usw_with_all_elements(meta):
    st, inv = meta
    c = find_ghcn_candidates(41.784, -87.755, st, inv, (1995, 2024))
    assert c.iloc[0]["id"] == "USW00014819"          # USW beats the longer co-op record
    assert "USW00094846" not in set(c["id"])          # ORD lacks TMIN in this fixture


def test_select_nearest_and_override():
    market = {"A": {"lat": 40.0, "lon": -88.0, "markets": ["rain"]},
              "B": {"lat": 42.0, "lon": -88.0, "markets": ["tmax"]},
              "C": {"lat": 40.1, "lon": -88.1, "markets": []},          # no market: skipped
              "D": {"lat": 30.0, "lon": -90.0, "markets": ["rain"]}}
    assert select_stations(40.1, -88.2, market, 2) == ["A", "B"]
    assert select_stations(40.1, -88.2, market, 2, explicit=["D"]) == ["D"]
    with pytest.warns(UserWarning, match="basis risk"):
        select_stations(20.0, -60.0, market, 1, max_km=400)


def test_closed_station_never_beats_live_airport(tmp_path):
    """Regression: PHL's GHCN name is 'PHILA INTL AP'; a 1945-52 'PHILADELPHIA NAAS' station
    matching the name hint must not be chosen."""
    (tmp_path / "s.txt").write_text(
        "USW00013739  39.8733  -75.2269    2.1 PA PHILA INTL AP\n"
        "USW00013771  39.8833  -75.1667    3.0 PA PHILADELPHIA NAAS\n")
    (tmp_path / "i.txt").write_text("".join(
        f"{i}  39.8733  -75.2269 {e} {a} {b}\n" for i, a, b in
        (("USW00013739", 1940, 2026), ("USW00013771", 1945, 1952)) for e in ("TMAX", "TMIN", "PRCP")))
    st, inv = parse_stations(tmp_path / "s.txt"), parse_inventory(tmp_path / "i.txt")
    from farmerjoe.stations import resolve_market_stations
    res = resolve_market_stations({"PHL": {"lat": 39.873, "lon": -75.227, "name_hint": "PHILADELPHIA",
                                           "markets": ["rain"]}}, st, inv, (1995, 2024),
                                  tmp_path / "cache.json", verify=False)
    assert res["PHL"].ghcn_id == "USW00013739"
