"""Route, carriers and model constants for the Germany -> NJ demo lane.

Hub networks are each carrier's publicly known main hubs; leg durations and
prices are placeholders until replaced by real data (Person A).
"""
from dataclasses import dataclass, field

# --- Places ---------------------------------------------------------------
PLACES = {
    # code: (name, lat, lon)
    "MUC_ORIGIN": ("Munich (shipper)", 48.137, 11.575),
    "LEJ": ("Leipzig/Halle (DHL hub)", 51.432, 12.241),
    "CGN": ("Cologne/Bonn (UPS hub)", 50.866, 7.143),
    "CDG": ("Paris CDG (FedEx hub)", 49.010, 2.548),
    "FRA": ("Frankfurt (Deutsche Post intl)", 50.038, 8.562),
    "CVG": ("Cincinnati (DHL Americas hub)", 39.049, -84.668),
    "SDF": ("Louisville (UPS Worldport)", 38.174, -85.736),
    "MEM": ("Memphis (FedEx hub)", 35.042, -89.977),
    "JFK": ("New York JFK (USPS ISC)", 40.641, -73.778),
    "PRINCETON_DEST": ("Princeton, NJ (recipient)", 40.357, -74.667),
}

# Weekday sets (Mon=0 .. Sun=6)
MON_FRI = frozenset({0, 1, 2, 3, 4})
MON_SAT = frozenset({0, 1, 2, 3, 4, 5})
ALL_DAYS = frozenset(range(7))


@dataclass(frozen=True)
class Leg:
    name: str
    frm: str
    to: str
    median_hours: float          # typical door-to-door time for this leg
    sigma: float                 # lognormal spread of the base duration
    weather_node: str | None     # airport whose weather can delay departure
    works_on: frozenset = ALL_DAYS
    delay_mean_hours: float = 24.0   # mean extra hours when a weather delay hits
    holiday_country: str | None = None  # "DE"/"US": leg doesn't run on that country's holidays
    customs_after: bool = False  # US customs clearance happens after this leg


@dataclass(frozen=True)
class Carrier:
    name: str
    service: str
    price_usd: float             # PLACEHOLDER - replace with Shippo live quote
    legs: tuple[Leg, ...] = field(default_factory=tuple)


CARRIERS: tuple[Carrier, ...] = (
    Carrier("DHL Express", "Worldwide Express", 182.0, (
        Leg("Pickup -> Leipzig", "MUC_ORIGIN", "LEJ", 10, 0.30, None, MON_FRI, holiday_country="DE"),
        Leg("Leipzig -> Cincinnati (air)", "LEJ", "CVG", 14, 0.25, "LEJ", MON_SAT, customs_after=True),
        Leg("Cincinnati -> Princeton", "CVG", "PRINCETON_DEST", 22, 0.35, "CVG", MON_FRI, holiday_country="US"),
    )),
    Carrier("UPS", "Worldwide Saver", 165.0, (
        Leg("Pickup -> Cologne", "MUC_ORIGIN", "CGN", 12, 0.30, None, MON_FRI, holiday_country="DE"),
        Leg("Cologne -> Louisville (air)", "CGN", "SDF", 15, 0.25, "CGN", MON_SAT, customs_after=True),
        Leg("Louisville -> Princeton", "SDF", "PRINCETON_DEST", 24, 0.35, "SDF", MON_FRI, holiday_country="US"),
    )),
    Carrier("FedEx", "International Priority", 171.0, (
        Leg("Pickup -> Paris CDG", "MUC_ORIGIN", "CDG", 20, 0.35, None, MON_FRI, holiday_country="DE"),
        Leg("Paris CDG -> Memphis (air)", "CDG", "MEM", 16, 0.25, "CDG", MON_SAT, customs_after=True),
        Leg("Memphis -> Princeton", "MEM", "PRINCETON_DEST", 26, 0.35, "MEM", MON_FRI, holiday_country="US"),
    )),
    Carrier("Deutsche Post + USPS", "Premium International", 58.0, (
        Leg("Pickup -> Frankfurt", "MUC_ORIGIN", "FRA", 30, 0.40, None, MON_SAT, holiday_country="DE"),
        Leg("Frankfurt -> JFK (air)", "FRA", "JFK", 48, 0.45, "FRA", MON_FRI, delay_mean_hours=36, customs_after=True),
        Leg("JFK ISC -> Princeton (USPS)", "JFK", "PRINCETON_DEST", 72, 0.50, "JFK", MON_SAT, holiday_country="US"),
    )),
)

# --- Customs (ASSUMED, identical for every carrier; shown with a disclaimer) --
CUSTOMS_MEDIAN_HOURS = 10.0
CUSTOMS_SIGMA = 0.9
CUSTOMS_DISCLAIMER = (
    "Customs delay is an assumed distribution applied equally to every carrier. "
    "No public per-shipment customs data exists, so carrier customs performance is not modeled."
)
SYNTHETIC_DISCLAIMER = "Carrier shipment history shown here is synthetic (demo only)."
PRICE_DISCLAIMER = "Prices are placeholders until live Shippo quotes are wired in."

# --- Weather ----------------------------------------------------------------
FORECAST_TRUST_DAYS = 7      # use forecast for days 0..7, climatology after
CLIMATOLOGY_YEARS = 3
WEATHER_VARS = ("precipitation_sum", "snowfall_sum", "wind_speed_10m_max", "temperature_2m_min")

N_SIMULATIONS = 10_000
PICKUP_HOUR = 14             # shipment handed over at 14:00 local on ship date
