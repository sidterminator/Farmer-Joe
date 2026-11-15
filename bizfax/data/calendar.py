"""Holidays and peak-season flags for DE and US."""
from __future__ import annotations

import datetime as dt
from functools import lru_cache

import holidays


@lru_cache(maxsize=None)
def _country(country: str, year: int) -> holidays.HolidayBase:
    return holidays.country_holidays(country, years=year)


def is_holiday(country: str, day: dt.date) -> bool:
    return day in _country(country, day.year)


def is_peak_season(day: dt.date) -> bool:
    """Parcel peak: Black Friday week through Dec 31 (approx: Nov 20 - Dec 31)."""
    return (day.month == 11 and day.day >= 20) or day.month == 12
