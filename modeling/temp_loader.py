"""Temporary loader for the modeling work.

Reads single series straight from the PSA OpenSTAT exports in datasets/raw/.
This is a stopgap until Member 1's cleaned data and database are ready; once
they are, replace these functions with calls to that data layer and keep the
same return type (a monthly pd.Series indexed by date).

The raw files are only read, never modified.
"""

from functools import lru_cache
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[1] / "datasets" / "raw"

# Last month PSA has released in the current exports. Later columns are "..".
LAST_RELEASED = "2026-08-01"

CPI_FILES = ["CPI_1.xlsx", "CPI_2.xlsx", "CPI_3.xlsx"]
INFLATION_FILES = ["Inflation_1.xlsx", "Inflation_2.xlsx"]
PURCHASING_POWER_FILES = ["PurchasingPower.xlsx"]


@lru_cache(maxsize=None)
def _read_openstat(path):
    """Parse one OpenSTAT Excel export into long format.

    Cached, because reading the Excel files is slow; callers must not modify
    the returned frame.

    Layout: row 0 is the title, row 2 holds the year (only above January),
    row 3 holds the month, and data starts at row 4 with the area in column 0
    (only on its first row) and the item in column 1. A blank row separates
    the data from PSA's notes.
    """
    sheet = pd.read_excel(path, header=None)

    years = sheet.iloc[2, 2:].ffill()
    months = sheet.iloc[3, 2:]
    periods = [f"{int(y)} {m}" for y, m in zip(years, months)]

    body = sheet.iloc[4:]
    blank = body.isna().all(axis=1)
    if blank.any():
        body = body.loc[: blank.idxmax() - 1]
    body = body.copy()
    body.columns = ["area", "item"] + periods
    body["area"] = body["area"].ffill()

    long = body.melt(id_vars=["area", "item"], var_name="period", value_name="value")
    long = long[~long["period"].str.endswith("Ave")]
    long["date"] = pd.to_datetime(long["period"], format="%Y %b")
    # ".." marks months PSA has not released yet.
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    return long[["area", "item", "date", "value"]]


def _load_series(files, area, item, name):
    frames = [_read_openstat(RAW_DIR / f) for f in files]
    data = pd.concat(frames).drop_duplicates(["area", "item", "date"])
    data = data[(data["area"] == area) & (data["date"] <= LAST_RELEASED)]
    if item is not None:
        data = data[data["item"] == item]
    if data.empty:
        raise ValueError(f"No rows for area={area!r}, item={item!r}")

    series = data.set_index("date")["value"].sort_index().astype(float)
    series = series.asfreq("MS")
    series.name = name
    if series.isna().any():
        missing = series[series.isna()].index.strftime("%Y-%m").tolist()
        raise ValueError(f"{name} has missing months: {missing}")
    return series


def load_cpi(area="PHILIPPINES", item="0 - ALL ITEMS"):
    """Monthly CPI (2018=100), Jan 2018 - Aug 2026."""
    return _load_series(CPI_FILES, area, item, "cpi")


def load_inflation(area="PHILIPPINES", item="0 - ALL ITEMS"):
    """Monthly year-on-year inflation rate in percent, Jan 2019 - Aug 2026."""
    return _load_series(INFLATION_FILES, area, item, "inflation")


def load_purchasing_power(area="PHILIPPINES"):
    """Monthly purchasing power of the peso (2018=100), Jan 2018 - Aug 2026."""
    return _load_series(PURCHASING_POWER_FILES, area, None, "purchasing_power")


# --- Full tables for the backend ---------------------------------------------
# Like the functions above, these are temporary: Member 1's preprocessing and
# database will provide the same tables.

FIES_FILE = "FIES.csv"

PRICE_FILES = {
    "cpi": CPI_FILES,
    "inflation": INFLATION_FILES,
    "purchasing_power": PURCHASING_POWER_FILES,
}

# The 18 regions, using the CPI files' names (without the leading dots), in
# PSA's usual order.
REGIONS = [
    "National Capital Region (NCR)",
    "Cordillera Administrative Region (CAR)",
    "Region I (Ilocos Region)",
    "Region II (Cagayan Valley)",
    "Region III (Central Luzon)",
    "Region IV-A (CALABARZON)",
    "MIMAROPA Region",
    "Region V (Bicol Region)",
    "Region VI (Western Visayas)",
    "Negros Island Region (NIR)",
    "Region VII (Central Visayas)",
    "Region VIII (Eastern Visayas)",
    "Region IX (Zamboanga Peninsula)",
    "Region X (Northern Mindanao)",
    "Region XI (Davao Region)",
    "Region XII (SOCCSKSARGEN)",
    "Region XIII (Caraga)",
    "Bangsamoro Autonomous Region in Muslim Mindanao (BARMM)",
]

# FIES region names (after removing footnote markers such as "2/") mapped to
# the CPI names above.
FIES_REGION_NAMES = {
    "NATIONAL CAPITAL REGION": "National Capital Region (NCR)",
    "CORDILLERA ADMINISTRATIVE REGION": "Cordillera Administrative Region (CAR)",
    "REGION I - ILOCOS REGION": "Region I (Ilocos Region)",
    "REGION II - CAGAYAN VALLEY": "Region II (Cagayan Valley)",
    "REGION III - CENTRAL LUZON": "Region III (Central Luzon)",
    "REGION IVA - CALABARZON": "Region IV-A (CALABARZON)",
    "MIMAROPA REGION": "MIMAROPA Region",
    "REGION V - BICOL REGION": "Region V (Bicol Region)",
    "REGION VI - WESTERN VISAYAS": "Region VI (Western Visayas)",
    "NEGROS ISLAND REGION (NIR)": "Negros Island Region (NIR)",
    "REGION VII - CENTRAL VISAYAS": "Region VII (Central Visayas)",
    "REGION VIII - EASTERN VISAYAS": "Region VIII (Eastern Visayas)",
    "REGION IX - ZAMBOANGA PENINSULA": "Region IX (Zamboanga Peninsula)",
    "REGION X - NORTHERN MINDANAO": "Region X (Northern Mindanao)",
    "REGION XI - DAVAO REGION": "Region XI (Davao Region)",
    "REGION XII - SOCCSKSARGEN": "Region XII (SOCCSKSARGEN)",
    "CARAGA": "Region XIII (Caraga)",
    "BANGSAMORO AUTONOMOUS REGION IN MUSLIM MINDANAO": "Bangsamoro Autonomous Region in Muslim Mindanao (BARMM)",
}

FIES_DECILES = [
    "All Income Groups", "First Decile", "Second Decile", "Third Decile", "Fourth Decile",
    "Fifth Decile", "Sixth Decile", "Seventh Decile", "Eighth Decile", "Ninth Decile", "Tenth Decile",
]


def _area_level(raw_name):
    """National, region, area group, or province/city, from PSA's leading dots."""
    if raw_name == "PHILIPPINES":
        return "national"
    name = raw_name.lstrip(".")
    if len(raw_name) - len(name) <= 2:
        return "area group" if name.startswith("Areas Outside") else "region"
    return "province/city"


@lru_cache(maxsize=None)
def load_price_table(indicator):
    """Every area and item for one indicator, in long format.

    Columns: area, area_level, item, date, value. Area names have PSA's
    leading dots removed. Purchasing power has no commodity breakdown, so its
    item is "0 - ALL ITEMS" (it is the reciprocal of all-items CPI).
    Cached; callers must not modify the returned frame.
    """
    if indicator not in PRICE_FILES:
        raise ValueError(f"Unknown indicator {indicator!r}; expected one of {list(PRICE_FILES)}")
    frames = [_read_openstat(RAW_DIR / f) for f in PRICE_FILES[indicator]]
    data = pd.concat(frames).drop_duplicates(["area", "item", "date"])
    data = data[data["date"] <= LAST_RELEASED].copy()

    data["area_level"] = data["area"].map(_area_level)
    data["area"] = data["area"].str.lstrip(".").str.strip()
    if indicator == "purchasing_power":
        data["item"] = "0 - ALL ITEMS"
    return data[["area", "area_level", "item", "date", "value"]].reset_index(drop=True)


@lru_cache(maxsize=None)
def load_fies():
    """2023 FIES average income, expenditure and savings (thousand pesos,
    constant 2021 prices) by area and per capita income decile.

    Columns: area, area_level, decile, income, expenditure, savings. Region
    names are mapped to the CPI names so the two can be joined.
    Cached; callers must not modify the returned frame.
    """
    raw = pd.read_csv(RAW_DIR / FIES_FILE, encoding="utf-8-sig")
    raw = raw.iloc[:, :4]
    raw.columns = ["area", "decile", "indicator", "value"]

    # Remove footnote markers ("SOCCSKSARGEN2/") and HUC indent dots.
    raw["area"] = raw["area"].str.replace(r"\d+/$", "", regex=True).str.lstrip(".").str.strip()
    raw["indicator"] = (raw["indicator"].str.extract(r"Average (\w+)", expand=False).str.lower())
    raw["value"] = pd.to_numeric(raw["value"], errors="coerce")

    wide = raw.pivot_table(index=["area", "decile"], columns="indicator", values="value", sort=False).reset_index()
    wide.columns.name = None

    is_region = wide["area"].isin(FIES_REGION_NAMES)
    wide["area_level"] = "province/city"
    wide.loc[is_region, "area_level"] = "region"
    wide.loc[wide["area"] == "PHILIPPINES", "area_level"] = "national"
    wide["area"] = wide["area"].replace(FIES_REGION_NAMES)
    wide["decile"] = pd.Categorical(wide["decile"], categories=FIES_DECILES, ordered=True)
    return wide[["area", "area_level", "decile", "income", "expenditure", "savings"]]
