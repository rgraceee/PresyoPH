"""
================================================================================
FILE: backend/sources.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
This file is the LOW-LEVEL DATA ACCESS module. It handles:
  1. Connecting to the MySQL database (presyoph_db) and running SQL queries.
  2. Reading forecasting output CSV files from datasets/outputs/.
  3. Caching all data so repeated calls don't hit the database or disk again.

This file is called by backend/data.py (the higher-level layer). The Streamlit
pages never call this file directly -- they go through backend/data.py.

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- backend/data.py: Imports from this file and calls functions like
  price_table(), fies_table(), forecasts_table(), metrics_table(),
  model_info(), series(), regions(). These functions are the bridge between
  the raw data (MySQL + CSVs) and the dashboard pages.
- modeling/run_pipeline.py: Writes the CSV files that this file reads
  (forecasts.csv, metrics.csv, model_info.json, etc.).
- data_pipeline/load_database.py: Loads data into MySQL that this file reads.
- tests/test_sources.py: Tests import from backend.sources and test these
  functions directly.

================================================================================
KEY DESIGN: CACHING
-------------------
Functions decorated with @lru_cache(maxsize=None) run their body only once.
The result is stored in memory and returned on every subsequent call. This
means:
  - The MySQL database is queried only once per table per session.
  - CSV files are read only once per file per session.
  - Callers must NOT modify returned DataFrames (the cached copy would change).
"""

import json                                          # json: reads model_info.json (forecast model metadata)
import os                                            # os: reads environment variables (DB_HOST, DB_PORT, etc.)
from functools import lru_cache                      # lru_cache: decorator that caches function results in memory
from pathlib import Path                             # Path: works with file system paths

import pandas as pd                                  # pandas: DataFrames for all data handling


# --- Module-level constants ---------------------------------------------------

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "datasets" / "outputs"
# Path to datasets/outputs/ folder. This is where modeling/run_pipeline.py
# writes forecast CSVs, metrics, and model_info.json. We read from here.

PRICE_TABLES = ("cpi", "inflation", "purchasing_power")
# Tuple of valid indicator names. Used to validate the indicator parameter
# in price_table() and other functions.

# FIES is a single 2023 snapshot (not a monthly time series).
FIES_YEAR = 2023                                      # The year of the FIES survey data we use.

# The 18 Philippine regions, in PSA's official order, without leading dots.
# These names match what's in the CPI database (after stripping dots).
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

# FIES region names use ALL CAPS and sometimes have footnote markers like "2/".
# This dictionary maps FIES names to CPI names so we can join FIES data with
# CPI region data.
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

# The 11 FIES income deciles in order from lowest to highest income.
FIES_DECILES = [
    "All Income Groups", "First Decile", "Second Decile", "Third Decile", "Fourth Decile",
    "Fifth Decile", "Sixth Decile", "Seventh Decile", "Eighth Decile", "Ninth Decile", "Tenth Decile",
]


# --- Low-level database query helper ------------------------------------------

def _query(sql, columns):
    """Run one SELECT query against presyoph_db and return results as a DataFrame.

    This is the ONLY function in this file that talks to MySQL. Every other
    data-reading function calls _query() or calls a function that calls _query().

    Parameters
    ----------
    sql : str
        A SQL SELECT statement.
    columns : list of str
        Column names for the resulting DataFrame.

    Returns
    -------
    pandas.DataFrame
        Query results with the given column names.

    Raises
    ------
    ConnectionError
        If MySQL cannot be reached (with helpful setup instructions).
    """
    import mysql.connector                               # MySQL driver: connects Python to MySQL/MariaDB

    # Read connection settings from environment variables, with XAMPP defaults.
    host = os.getenv("DB_HOST", "localhost")             # Database host (default: localhost)
    port = int(os.getenv("DB_PORT", "3306"))             # Database port (default: 3306, MySQL standard)
    database = os.getenv("DB_NAME", "presyoph_db")       # Database name (default: presyoph_db)
    try:
        conn = mysql.connector.connect(                  # Open a connection to MySQL
            host=host,
            port=port,
            user=os.getenv("DB_USER", "root"),           # DB user (default: root, XAMPP default)
            password=os.getenv("DB_PASSWORD", ""),       # DB password (default: empty, XAMPP default)
            database=database,
        )
    except mysql.connector.Error as err:                 # If connection fails
        raise ConnectionError(                           # Raise a clear error with setup instructions
            f"Cannot reach the {database} database at {host}:{port} ({err.msg}). "
            "Start MySQL in the XAMPP Control Panel and make sure the database is "
            "imported; see 'Database' in README.md."
        ) from err
    try:
        cursor = conn.cursor()                           # Create a cursor to run SQL
        try:
            cursor.execute(sql)                          # Execute the SQL query
            return pd.DataFrame(cursor.fetchall(), columns=columns)  # Convert rows to a DataFrame
        finally:
            cursor.close()                               # Always close the cursor
    finally:
        conn.close()                                     # Always close the connection


def _area_level(raw_name):
    """Determine the area level from PSA's raw area name (which uses leading dots).

    PSA uses leading dots to show geographic hierarchy:
    - "PHILIPPINES" -> national
    - "..Region I (...)" -> region (2 dots)
    - "....Abra" -> province/city (4 dots)
    - "..Areas Outside ..." -> area group

    Parameters
    ----------
    raw_name : str
        The area name as stored in the database (with leading dots).

    Returns
    -------
    str
        One of: "national", "region", "area group", "province/city".
    """
    if raw_name == "PHILIPPINES":                        # National level has no dots and is named PHILIPPINES
        return "national"
    name = raw_name.lstrip(".")                          # Remove all leading dots to get the clean name
    # PSA uses leading dots to show hierarchy: <= 2 dots = region, more = province/city.
    if name.startswith("Areas Outside"):                 # "Areas Outside NCR" is an area group
        return "area group"
    if len(raw_name) - len(name) <= 2:                   # 2 or fewer dots = region level
        return "region"
    return "province/city"                               # More than 2 dots = province or city


# --- Price table (CPI, inflation, purchasing power) ---------------------------
# This is the most important data source. It returns all price data as one table.

@lru_cache(maxsize=None)                                 # Cache result: run SQL once, reuse forever
def price_table(indicator):
    """Return all price data for one indicator as a DataFrame.

    Columns: area, area_level, item, date, value.
    Area names have PSA's leading dots removed. Purchasing power has no
    commodity breakdown, so its item is always "0 - ALL ITEMS".

    Parameters
    ----------
    indicator : str
        One of "cpi", "inflation", "purchasing_power".

    Returns
    -------
    pandas.DataFrame
        Columns: area, area_level, item, date, value.

    Raises
    ------
    ValueError
        If indicator is not one of the valid price tables.
    """
    if indicator not in PRICE_TABLES:                    # Validate indicator name
        raise ValueError(f"Unknown indicator {indicator!r}; expected one of {list(PRICE_TABLES)}")

    if indicator == "purchasing_power":                  # Purchasing power uses a different table, no category breakdown
        sql = """
            SELECT a.area_name, '0 - ALL ITEMS', p.date, p.value
            FROM purchasing_power p
            JOIN areas a ON p.area_id = a.area_id
        """
    else:                                                # CPI and inflation have category breakdowns
        sql = f"""
            SELECT a.area_name, c.category_name, p.date, p.value
            FROM {indicator} p
            JOIN areas a ON p.area_id = a.area_id
            JOIN categories c ON p.category_id = c.category_id
        """
    data = _query(sql, ["area", "item", "date", "value"])  # Run the SQL query and get a DataFrame

    data["area_level"] = data["area"].map(_area_level)   # Add area_level column using _area_level()
    data["area"] = data["area"].str.lstrip(".").str.strip()  # Remove leading dots and whitespace from area names
    # MySQL dates arrive as second resolution; convert to pandas datetime64[us].
    data["date"] = pd.to_datetime(data["date"]).astype("datetime64[us]")
    data["value"] = pd.to_numeric(data["value"]).astype(float)  # Ensure value column is float
    return data[["area", "area_level", "item", "date", "value"]]  # Return only the needed columns in order


def series(indicator, area="PHILIPPINES", item="0 - ALL ITEMS"):
    """Return one monthly time series as a pandas Series indexed by month start.

    This is a lower-level function than backend/data.get_series(). It returns
    a pd.Series (not a DataFrame) with date as the index. It also validates
    that there are no missing months.

    Parameters
    ----------
    indicator : str
        One of "cpi", "inflation", "purchasing_power".
    area : str
        Area name without leading dots (default "PHILIPPINES").
    item : str
        Item label (default "0 - ALL ITEMS").

    Returns
    -------
    pandas.Series
        Indexed by month start, values are the indicator values.

    Raises
    ------
    ValueError
        If the series is empty or has missing months.
    """
    data = price_table(indicator)                          # Get the full price table (cached)
    data = data[(data["area"] == area) & (data["item"] == item)]  # Filter to this area and item
    if data.empty:                                         # No matching rows = invalid area/item
        raise ValueError(f"No {indicator} rows for area={area!r}, item={item!r}")

    values = data.set_index("date")["value"].sort_index().asfreq("MS")  # Set date as index, sort, ensure monthly frequency
    values.name = indicator                                # Name the series after the indicator
    if values.isna().any():                                # Check for missing months
        missing = values[values.isna()].index.strftime("%Y-%m").tolist()  # List which months are missing
        raise ValueError(f"{indicator} has missing months: {missing}")
    return values                                          # Return the clean monthly series


# --- FIES table ----------------------------------------------------------------
# FIES is a 2023 snapshot, not monthly. It's stored differently in the database.

@lru_cache(maxsize=None)                                 # Cache result
def fies_table():
    """Return FIES data as a wide DataFrame.

    Columns: area, area_level, decile, income, expenditure, savings.
    2023 FIES averages in thousand pesos. Region names are mapped to CPI names.

    Returns
    -------
    pandas.DataFrame
        One row per (area, decile) combination.
    """
    data = _query(                                         # Query the fies table for 2023
        f"SELECT area, income_group, indicator, value FROM fies WHERE year = {FIES_YEAR}",
        ["area", "decile", "indicator", "value"],
    )

    # Remove footnote markers ("SOCCSKSARGEN2/") and HUC indent dots from area names.
    data["area"] = data["area"].str.replace(r"\d+/$", "", regex=True).str.lstrip(".").str.strip()
    # Extract the measure name from indicators like "Average Income (in thousand pesos)".
    data["indicator"] = data["indicator"].str.extract(r"Average (\w+)", expand=False).str.lower()
    data["value"] = pd.to_numeric(data["value"]).astype(float)  # Ensure values are numeric

    # Pivot from long format (one row per indicator) to wide (one column per indicator).
    wide = data.pivot_table(index=["area", "decile"], columns="indicator", values="value",
                            aggfunc="first").reset_index()
    wide.columns.name = None                               # Remove the columns axis name

    # Classify each area as region, province/city, or national.
    is_region = wide["area"].isin(FIES_REGION_NAMES)       # Which areas are regions (in our mapping)?
    wide["area_level"] = "province/city"                   # Default: province/city
    wide.loc[is_region, "area_level"] = "region"           # Override: regions
    wide.loc[wide["area"] == "PHILIPPINES", "area_level"] = "national"  # Override: national
    wide["area"] = wide["area"].replace(FIES_REGION_NAMES)  # Replace FIES names with CPI names

    # Align province/city names with CPI area labels (case-insensitive match).
    cpi_areas = price_table("cpi")["area"].unique()        # Get all area names from CPI data
    area_lookup = {name.upper(): name for name in cpi_areas}  # Build lookup: uppercase name -> proper name
    wide["area"] = wide["area"].map(lambda name: area_lookup.get(name.upper(), name))  # Match FIES area to CPI area name

    wide["decile"] = pd.Categorical(wide["decile"], categories=FIES_DECILES, ordered=True)  # Make decile an ordered category
    return wide[["area", "area_level", "decile", "income", "expenditure", "savings"]]  # Return final columns


def regions():
    """Return the 18 region names in PSA order.
    
    Returns
    -------
    list of str
        Region names.
    """
    return list(REGIONS)                                   # Return a copy of the REGIONS list


# --- Forecasting output readers -----------------------------------------------
# These read CSV files written by modeling/run_pipeline.py.

def _read_output(name, dates=()):
    """Read a CSV file from datasets/outputs/.

    Parameters
    ----------
    name : str
        Filename (e.g. "forecasts.csv").
    dates : tuple of str
        Column names to parse as dates.

    Returns
    -------
    pandas.DataFrame

    Raises
    ------
    FileNotFoundError
        If the file doesn't exist (tells user to run the pipeline first).
    """
    path = OUTPUT_DIR / name                               # Full path to the output file
    if not path.exists():                                  # If file doesn't exist
        raise FileNotFoundError(                           # Tell user to run the modeling pipeline
            f"{path} not found. Run `python -m modeling.run_pipeline` to create the forecasting outputs."
        )
    return pd.read_csv(path, parse_dates=list(dates))      # Read CSV, parsing date columns


@lru_cache(maxsize=None)                                 # Cache result
def forecasts_table():
    """Return the forecasts table.
    
    Columns: origin, model, variable, date, step, forecast, lower, upper, is_selected.
    
    Returns
    -------
    pandas.DataFrame
    """
    return _read_output("forecasts.csv", dates=("origin", "date"))  # Read forecasts.csv with date parsing


@lru_cache(maxsize=None)                                 # Cache result
def test_predictions_table():
    """Return the test predictions table.
    
    Columns: evaluation, origin, model, variable, date, step, forecast, lower, upper, actual, error.
    
    Returns
    -------
    pandas.DataFrame
    """
    return _read_output("test_predictions.csv", dates=("origin", "date"))  # Read test_predictions.csv


@lru_cache(maxsize=None)                                 # Cache result
def metrics_table():
    """Return the model evaluation metrics table.
    
    Columns: evaluation, period, model, variable, mae, rmse, mape, n_months,
    is_selected_model, used_for_selection.
    
    Returns
    -------
    pandas.DataFrame
    """
    return _read_output("metrics.csv")                     # Read metrics.csv


@lru_cache(maxsize=None)                                 # Cache result
def error_by_step_table():
    """Return the error-by-step table.
    
    Columns: variable, model, step, mae.
    
    Returns
    -------
    pandas.DataFrame
    """
    return _read_output("error_by_step.csv")               # Read error_by_step.csv


@lru_cache(maxsize=None)                                 # Cache result
def model_info():
    """Return the model info dictionary from model_info.json.
    
    Contains: final_model, selection rule, data period, forecast settings,
    model parameters, and notes.
    
    Returns
    -------
    dict
    """
    path = OUTPUT_DIR / "model_info.json"                  # Path to model_info.json
    if not path.exists():                                  # If file doesn't exist
        raise FileNotFoundError(                           # Tell user to run the pipeline
            f"{path} not found. Run `python -m modeling.run_pipeline` to create the forecasting outputs."
        )
    return json.loads(path.read_text(encoding="utf-8"))    # Read and parse the JSON file


def clear_cache():
    """Clear all cached data and outputs.
    
    Call this after re-importing the database or re-running the forecasting
    pipeline so the next data fetch gets fresh results.
    """
    for fn in (price_table, fies_table, forecasts_table, test_predictions_table,
               metrics_table, error_by_step_table, model_info):  # All cached functions
        fn.cache_clear()                                   # Clear each function's cache
