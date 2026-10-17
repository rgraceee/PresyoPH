"""Where the backend and the modeling code get their data.

Historical data comes from the presyoph_db MySQL database built by
data_pipeline/ (see the README for setup). Forecasting outputs come from
datasets/outputs/, written by modeling/run_pipeline.py.

Connection settings are read from the DB_HOST, DB_PORT, DB_USER, DB_PASSWORD
and DB_NAME environment variables, defaulting to XAMPP's local root login.

All table functions are cached. Callers must not modify the returned frames.
"""

import json
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "datasets" / "outputs"

PRICE_TABLES = ("cpi", "inflation", "purchasing_power")

# FIES is a single 2023 snapshot (proposal, Data Sources).
FIES_YEAR = 2023

# The 18 regions, using the CPI names (without the leading dots), in PSA's
# usual order.
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


def _query(sql, columns):
    """Run one SELECT against presyoph_db and return the rows as a DataFrame.

    Raises ConnectionError with setup instructions if the database cannot be
    reached.
    """
    import mysql.connector

    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "3306"))
    database = os.getenv("DB_NAME", "presyoph_db")
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=database,
        )
    except mysql.connector.Error as err:
        raise ConnectionError(
            f"Cannot reach the {database} database at {host}:{port} ({err.msg}). "
            "Start MySQL in the XAMPP Control Panel and make sure the database is "
            "imported; see 'Database' in README.md."
        ) from err
    try:
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            return pd.DataFrame(cursor.fetchall(), columns=columns)
        finally:
            cursor.close()
    finally:
        conn.close()


def _area_level(raw_name):
    """National, region, area group, or province/city, from PSA's leading dots."""
    if raw_name == "PHILIPPINES":
        return "national"
    name = raw_name.lstrip(".")
    if name.startswith("Areas Outside"):
        return "area group"
    if len(raw_name) - len(name) <= 2:
        return "region"
    return "province/city"


@lru_cache(maxsize=None)
def price_table(indicator):
    """Columns: area, area_level, item, date, value.

    Area names have PSA's leading dots removed. Purchasing power has no
    commodity breakdown, so its item is "0 - ALL ITEMS".
    """
    if indicator not in PRICE_TABLES:
        raise ValueError(f"Unknown indicator {indicator!r}; expected one of {list(PRICE_TABLES)}")

    if indicator == "purchasing_power":
        sql = """
            SELECT a.area_name, '0 - ALL ITEMS', p.date, p.value
            FROM purchasing_power p
            JOIN areas a ON p.area_id = a.area_id
        """
    else:
        sql = f"""
            SELECT a.area_name, c.category_name, p.date, p.value
            FROM {indicator} p
            JOIN areas a ON p.area_id = a.area_id
            JOIN categories c ON p.category_id = c.category_id
        """
    data = _query(sql, ["area", "item", "date", "value"])

    data["area_level"] = data["area"].map(_area_level)
    data["area"] = data["area"].str.lstrip(".").str.strip()
    # MySQL dates arrive as second resolution; use pandas' default (us).
    data["date"] = pd.to_datetime(data["date"]).astype("datetime64[us]")
    data["value"] = pd.to_numeric(data["value"]).astype(float)
    return data[["area", "area_level", "item", "date", "value"]]


def series(indicator, area="PHILIPPINES", item="0 - ALL ITEMS"):
    """One monthly series as a float pd.Series indexed by month start.

    `area` is the name without PSA's leading dots, as in price_table().
    Raises ValueError if the series is empty or has missing months.
    """
    data = price_table(indicator)
    data = data[(data["area"] == area) & (data["item"] == item)]
    if data.empty:
        raise ValueError(f"No {indicator} rows for area={area!r}, item={item!r}")

    values = data.set_index("date")["value"].sort_index().asfreq("MS")
    values.name = indicator
    if values.isna().any():
        missing = values[values.isna()].index.strftime("%Y-%m").tolist()
        raise ValueError(f"{indicator} has missing months: {missing}")
    return values


@lru_cache(maxsize=None)
def fies_table():
    """Columns: area, area_level, decile, income, expenditure, savings.

    2023 FIES averages in thousand pesos. Region names are mapped to the CPI
    names so the two can be joined.
    """
    data = _query(
        f"SELECT area, income_group, indicator, value FROM fies WHERE year = {FIES_YEAR}",
        ["area", "decile", "indicator", "value"],
    )

    # Remove footnote markers ("SOCCSKSARGEN2/") and HUC indent dots.
    data["area"] = data["area"].str.replace(r"\d+/$", "", regex=True).str.lstrip(".").str.strip()
    data["indicator"] = data["indicator"].str.extract(r"Average (\w+)", expand=False).str.lower()
    data["value"] = pd.to_numeric(data["value"]).astype(float)

    wide = data.pivot_table(index=["area", "decile"], columns="indicator", values="value",
                            aggfunc="first").reset_index()
    wide.columns.name = None

    is_region = wide["area"].isin(FIES_REGION_NAMES)
    wide["area_level"] = "province/city"
    wide.loc[is_region, "area_level"] = "region"
    wide.loc[wide["area"] == "PHILIPPINES", "area_level"] = "national"
    wide["area"] = wide["area"].replace(FIES_REGION_NAMES)

    # Align province/city names with the CPI area labels.
    cpi_areas = price_table("cpi")["area"].unique()
    area_lookup = {name.upper(): name for name in cpi_areas}
    wide["area"] = wide["area"].map(lambda name: area_lookup.get(name.upper(), name))

    wide["decile"] = pd.Categorical(wide["decile"], categories=FIES_DECILES, ordered=True)
    return wide[["area", "area_level", "decile", "income", "expenditure", "savings"]]


def regions():
    """The 18 region names, in PSA order."""
    return list(REGIONS)


def _read_output(name, dates=()):
    path = OUTPUT_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python -m modeling.run_pipeline` to create the forecasting outputs."
        )
    return pd.read_csv(path, parse_dates=list(dates))


@lru_cache(maxsize=None)
def forecasts_table():
    """Columns: origin, model, variable, date, step, forecast, lower, upper, is_selected."""
    return _read_output("forecasts.csv", dates=("origin", "date"))


@lru_cache(maxsize=None)
def test_predictions_table():
    """Columns: evaluation, origin, model, variable, date, step, forecast, lower, upper, actual, error."""
    return _read_output("test_predictions.csv", dates=("origin", "date"))


@lru_cache(maxsize=None)
def metrics_table():
    """Columns: evaluation, period, model, variable, mae, rmse, mape, n_months,
    is_selected_model, used_for_selection."""
    return _read_output("metrics.csv")


@lru_cache(maxsize=None)
def error_by_step_table():
    """Columns: variable, model, step, mae."""
    return _read_output("error_by_step.csv")


@lru_cache(maxsize=None)
def model_info():
    path = OUTPUT_DIR / "model_info.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python -m modeling.run_pipeline` to create the forecasting outputs."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def clear_cache():
    """Forget cached data and outputs, e.g. after re-importing the database or
    re-running the pipeline."""
    for fn in (price_table, fies_table, forecasts_table, test_predictions_table,
               metrics_table, error_by_step_table, model_info):
        fn.cache_clear()
