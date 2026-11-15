"""bizfax - pre-booking carrier screen for small-business international parcels.

    streamlit run app.py
"""
import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from bizfax.config import (CARRIERS, CUSTOMS_DISCLAIMER, PLACES, PRICE_DISCLAIMER,
                           SYNTHETIC_DISCLAIMER)
from bizfax.model.simulate import HORIZON_DAYS, simulate_carrier, summarize
from bizfax.model.weather_delay import delay_probability
from bizfax.recommend import recommend

st.set_page_config(page_title="bizfax", layout="wide")
st.title("bizfax")
st.caption("Which carrier actually gets your parcel there on time? Germany → Princeton, NJ")

nodes = sorted({leg.weather_node for c in CARRIERS for leg in c.legs if leg.weather_node})


@st.cache_data(ttl=3600, show_spinner="Fetching hub weather…")
def hub_delay_probs(ship_date: dt.date) -> dict[str, pd.Series]:
    from bizfax.data.weather import weather_for_window
    end = ship_date + dt.timedelta(days=HORIZON_DAYS - 1)
    out = {}
    for code in nodes:
        w = weather_for_window(code, ship_date, end)
        out[code] = delay_probability(w)
    return out


with st.sidebar:
    ship_date = st.date_input("Ship date", dt.date.today())
    deadline = st.date_input("Needed by", dt.date.today() + dt.timedelta(days=6))
    use_weather = st.toggle("Use hub weather", value=True)

try:
    probs = hub_delay_probs(ship_date) if use_weather else {}
except Exception as e:  # network down at the venue -> still demo
    st.warning(f"Weather unavailable ({e}); running without weather.")
    probs = {}

rows, sims = [], {}
for c in CARRIERS:
    hours = simulate_carrier(c, ship_date, probs)
    sims[c.name] = hours
    rows.append({"carrier": c.name, "service": c.service, "price_usd": c.price_usd,
                 **summarize(hours, ship_date, deadline)})

rec = recommend(rows, deadline)
if rec["pick"]:
    st.success(f"**Book {rec['pick']['carrier']}** (${rec['pick']['price_usd']:.0f}). {rec['reason']}")
else:
    st.error(rec["reason"])

col1, col2 = st.columns([3, 2])
with col1:
    st.subheader("Projected delivery (80% interval)")
    fig = go.Figure()
    for r in rows:
        fig.add_trace(go.Scatter(
            x=[r["p10"], r["p90"]], y=[r["carrier"]] * 2, mode="lines",
            line=dict(width=14), name=r["carrier"], showlegend=False))
        fig.add_trace(go.Scatter(x=[r["p50"]], y=[r["carrier"]], mode="markers",
                                 marker=dict(size=14, color="black", symbol="line-ns-open"), showlegend=False))
    fig.add_vline(x=pd.Timestamp(deadline), line_dash="dash", annotation_text="needed by")
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    table = pd.DataFrame(rows)[["carrier", "service", "price_usd", "p10", "p50", "p90", "p_on_time"]]
    table["p_on_time"] = (table["p_on_time"] * 100).round(0).astype(int).astype(str) + "%"
    st.dataframe(table, hide_index=True, use_container_width=True)

with col2:
    st.subheader("Routes")
    fig = go.Figure()
    for c in CARRIERS:
        stops = [c.legs[0].frm] + [leg.to for leg in c.legs]
        fig.add_trace(go.Scattergeo(
            lon=[PLACES[s][2] for s in stops], lat=[PLACES[s][1] for s in stops],
            text=[PLACES[s][0] for s in stops], mode="lines+markers", name=c.name))
    fig.update_geos(projection_type="natural earth", lataxis_range=[25, 60], lonaxis_range=[-100, 20])
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

    if probs:
        st.subheader("Hub weather risk")
        risk = pd.DataFrame(probs).iloc[:10].T
        risk.columns = [d.strftime("%a %d") for d in risk.columns]
        st.dataframe((risk * 100).round(0), use_container_width=True)

st.caption(f"⚠️ {CUSTOMS_DISCLAIMER}")
st.caption(f"⚠️ {SYNTHETIC_DISCLAIMER} {PRICE_DISCLAIMER}")
