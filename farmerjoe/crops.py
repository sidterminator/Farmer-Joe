"""Crop calendar -> season window (CLAUDE.md 6.0; table in config.yaml, from REVENUE_MODEL.md §4)."""
from __future__ import annotations

import calendar as _cal
import datetime as dt
from typing import Any


def _check_crop(crop: str, table: dict[str, Any]) -> dict[str, Any]:
    if crop not in table:
        raise ValueError(f"unknown crop {crop!r}; valid crops: {sorted(table)}")
    row = table[crop]
    if not 1 <= row["start_month"] <= row["end_month"] <= 12:
        raise ValueError(f"crop {crop!r}: window must be whole months within one calendar year")
    return row


def default_year(crop: str, table: dict[str, Any], today: dt.date | None = None) -> int:
    """Next season for `crop` that has not started yet."""
    today = today or dt.date.today()
    row = _check_crop(crop, table)
    return today.year if today < dt.date(today.year, row["start_month"], 1) else today.year + 1


def season_window(crop: str, year: int, table: dict[str, Any]) -> tuple[dt.date, dt.date]:
    """(start, end) dates of the crop's critical weather window in `year` (whole months)."""
    row = _check_crop(crop, table)
    start = dt.date(year, row["start_month"], 1)
    end = dt.date(year, row["end_month"], _cal.monthrange(year, row["end_month"])[1])
    return start, end
