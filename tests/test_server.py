"""API sanity checks (uses the cached demo run if present; skips otherwise)."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import server
from farmerjoe.webcache import WEB_RUNS, run_id_for

CHAMPAIGN = dict(lat=40.12, lon=-88.24, crop="corn", acres=150, budget=40000, stability=1.0, stationId="ind")
cached = (WEB_RUNS / run_id_for(40.12, -88.24, "corn") / "run_meta.json").exists()
client = TestClient(server.app)


def test_soybean_price_for_corn_is_rejected():
    r = client.post("/api/scenario", json={**CHAMPAIGN, "yield": 200, "price": 10.0})
    assert r.status_code == 422 and "not plausible for corn" in r.text


@pytest.mark.skipif(not cached, reason="demo run not cached (run: python run.py --prewarm)")
def test_corn_default_passes_and_strikes_near_futures():
    r = client.post("/api/scenario", json={**CHAMPAIGN, "yield": 200, "price": 4.5})
    assert r.status_code == 200
    d = r.json()
    import numpy as np
    assert abs(np.mean(d["revenue"]) / (150 * 200 * 4.5) - 1) < 0.25
    qs = [m["question"] for m in d["markets"] if m["id"].startswith("price_")]
    assert any("$3.60" in q for q in qs) and not any("$9.00" in q for q in qs)


def test_price_ranges_match_server_check():
    r = client.get("/api/price-ranges").json()
    assert r["corn"] == {"lo": 2.25, "hi": 9.0}
    assert set(r) == {"corn", "soybeans", "wheat"}
    # the server accepts the edges of the range the form shows
    for price, code in ((r["corn"]["hi"], None), (r["corn"]["hi"] + 0.01, 422)):
        if code:
            assert client.post("/api/scenario", json={**CHAMPAIGN, "yield": 200, "price": price}).status_code == code
