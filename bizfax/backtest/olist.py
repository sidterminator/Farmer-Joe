"""Backtest delivery-time intervals on the real Olist dataset (Brazil, 2016-18).

Download from Kaggle "olistbr/brazilian-ecommerce" into data/raw/olist/.

Model (baseline Person B should beat): empirical P10/P50/P90 of transit days per
seller_state -> customer_state lane, fit on orders before the cutoff, evaluated after.
Compared against Olist's own promised date (order_estimated_delivery_date).

    python -m bizfax.backtest.olist --data data/raw/olist --cutoff 2018-01-01
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from bizfax.backtest.metrics import coverage, mean_width, pinball_loss

MIN_LANE_N = 30


def load(folder: str | Path) -> pd.DataFrame:
    f = Path(folder)
    orders = pd.read_csv(f / "olist_orders_dataset.csv", parse_dates=[
        "order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"])
    customers = pd.read_csv(f / "olist_customers_dataset.csv", usecols=["customer_id", "customer_state"])
    items = pd.read_csv(f / "olist_order_items_dataset.csv", usecols=["order_id", "seller_id"])
    sellers = pd.read_csv(f / "olist_sellers_dataset.csv", usecols=["seller_id", "seller_state"])

    first_seller = items.drop_duplicates("order_id").merge(sellers, on="seller_id")
    df = (orders[orders["order_status"] == "delivered"]
          .dropna(subset=["order_delivered_customer_date"])
          .merge(customers, on="customer_id")
          .merge(first_seller[["order_id", "seller_state"]], on="order_id"))
    df["transit_days"] = (df["order_delivered_customer_date"] - df["order_purchase_timestamp"]).dt.days
    df["promised_days"] = (df["order_estimated_delivery_date"] - df["order_purchase_timestamp"]).dt.days
    df["lane"] = df["seller_state"] + "->" + df["customer_state"]
    return df


def fit_quantiles(train: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    q = lambda g: g["transit_days"].quantile([0.1, 0.5, 0.9]).set_axis(["q10", "q50", "q90"])
    lane = train.groupby("lane").filter(lambda g: len(g) >= MIN_LANE_N).groupby("lane").apply(q)
    dest = train.groupby("customer_state").apply(q)
    return lane, dest


def predict(test: pd.DataFrame, lane_q: pd.DataFrame, dest_q: pd.DataFrame) -> pd.DataFrame:
    pred = test[["lane"]].join(lane_q, on="lane")
    fallback = test[["customer_state"]].join(dest_q, on="customer_state")
    return pred[["q10", "q50", "q90"]].fillna(fallback[["q10", "q50", "q90"]])


def run(folder: str, cutoff: str) -> dict:
    df = load(folder)
    train = df[df["order_purchase_timestamp"] < cutoff]
    test = df[df["order_purchase_timestamp"] >= cutoff]
    pred = predict(test, *fit_quantiles(train)).dropna()
    y = test.loc[pred.index, "transit_days"].to_numpy()
    promised = test.loc[pred.index, "promised_days"].to_numpy()
    return {
        "n_train": len(train), "n_test": len(pred),
        "coverage_80": coverage(y, pred["q10"], pred["q90"]),
        "mean_width_days": mean_width(pred["q10"], pred["q90"]),
        "pinball_q50": pinball_loss(y, pred["q50"], 0.5),
        "pinball_q90": pinball_loss(y, pred["q90"], 0.9),
        "our_p90_on_time_rate": float(np.mean(y <= pred["q90"])),
        "olist_promise_on_time_rate": float(np.mean(y <= promised)),
        "olist_promise_mean_days": float(np.mean(promised)),
        "our_p90_mean_days": float(pred["q90"].mean()),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/raw/olist")
    ap.add_argument("--cutoff", default="2018-01-01")
    args = ap.parse_args()
    for k, v in run(args.data, args.cutoff).items():
        print(f"{k:28s} {v:.3f}" if isinstance(v, float) else f"{k:28s} {v}")
