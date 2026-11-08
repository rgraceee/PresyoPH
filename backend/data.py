"""
Backend functions for the PresyoPH dashboard (task 6).

================================================================================
WHAT THIS FILE IS FOR:
================================================================================
This file is the DATA ACCESS LAYER for the PresyoPH dashboard. Every Streamlit
page (in app/pages/) calls functions from this file to get data. The pages
never read database tables or CSV files directly -- they always go through
the functions in this file.

This design means: if Member 1 changes the database (for example, moves from
MySQL to PostgreSQL), only backend/sources.py needs to change. This file
(stays the same) because it calls sources.py functions, not SQL directly.

================================================================================
HOW IT CONNECTS TO OTHER FILES:
================================================================================
- backend/sources.py: This file imports from sources (line 20). sources.py
  handles the low-level work: connecting to MySQL, reading CSVs, caching data.
  This file calls sources.price_table(), sources.fies_table(),
  sources.forecasts_table(), sources.metrics_table(), etc.
- app/pages/*.py: Every page imports from backend.data and calls functions
  like get_cpi(), get_latest(), get_forecast(), get_category_comparison(), etc.
- tests/test_backend.py: Tests import from backend.data and call these
  functions to verify they return correct data.

================================================================================
CONVENTIONS (important for understanding the code):
================================================================================
- Indicators: "cpi" (Consumer Price Index, 2018 = 100), "inflation"
  (year-on-year percentage change), "purchasing_power" (pesos, 2018 = 1.00).
- Dates are the first day of the month. start and end accept anything pandas
  can parse ("2020-01", "2020-01-01", a Timestamp) and are inclusive.
- Areas use PSA's names without leading dots, e.g. "PHILIPPINES",
  "National Capital Region (NCR)".
- Functions return pandas DataFrames or plain dicts. Invalid arguments raise
  ValueError with a message that can be shown to the user.
"""

import pandas as pd                                    # pandas: data manipulation library for DataFrames

from backend import sources                            # imports the low-level data access module (MySQL queries, CSV reading, caching)

# --- Module-level constants ---------------------------------------------------

INDICATORS = ("cpi", "inflation", "purchasing_power")   # Tuple of the three indicator names used throughout the app. Used for validation and iteration.
NATIONAL = "PHILIPPINES"                                # The national-level area name (PSA uses "PHILIPPINES" for the whole country).
ALL_ITEMS = "0 - ALL ITEMS"                             # PSA's item code for "all items" (the aggregate across all 13 commodity groups).
FORECAST_HORIZONS = range(1, 13)                        # Valid forecast horizons: 1 through 12 months ahead.
EVALUATIONS = ("pooled", "main_test", "rolling_fold", "rolling_average")  # Valid evaluation types for model metrics.

# Human-readable names for each indicator (used in chart titles, card labels).
INDICATOR_LABELS = {
    "cpi": "Consumer Price Index (2018 = 100)",
    "inflation": "Inflation rate (%)",
    "purchasing_power": "Purchasing power of the peso",
}

# Short labels for the 13 commodity groups, keyed by PSA's two-digit code.
# PSA category names look like "01 - FOOD AND NON-ALCOHOLIC BEVERAGES".
# The code (e.g. "01") maps to a short display name (e.g. "Food and non-alcoholic beverages").
CATEGORY_LABELS = {
    "01": "Food and non-alcoholic beverages",
    "02": "Alcoholic beverages and tobacco",
    "03": "Clothing and footwear",
    "04": "Housing, water, electricity, gas and other fuels",
    "05": "Furnishings, household equipment and maintenance",
    "06": "Health",
    "07": "Transport",
    "08": "Information and communication",
    "09": "Recreation, sport and culture",
    "10": "Education services",
    "11": "Restaurants and accommodation services",
    "12": "Financial services",
    "13": "Personal care and miscellaneous goods and services",
}


# --- Validation helpers ------------------------------------------------------
# These are "private" functions (names start with _) used only inside this file.
# They validate inputs before the main functions use them.

def _check_indicator(indicator):
    """Validate that `indicator` is one of the three known indicators.
    
    Parameters
    ----------
    indicator : str
        The indicator name to validate.
    
    Raises
    ------
    ValueError
        If indicator is not "cpi", "inflation", or "purchasing_power".
    """
    if indicator not in INDICATORS:                       # Check if the indicator string is in our allowed tuple
        raise ValueError(f"Unknown indicator {indicator!r}. Choose one of: {', '.join(INDICATORS)}.")  # Raise error with helpful message listing valid options


def _check_horizon(horizon):
    """Validate that `horizon` is between 1 and 12 months.
    
    Parameters
    ----------
    horizon : int
        The forecast horizon to validate.
    
    Raises
    ------
    ValueError
        If horizon is not in range 1-12.
    """
    if horizon not in FORECAST_HORIZONS:                   # Check if horizon is in the valid range 1-12
        raise ValueError(f"Horizon must be between 1 and 12 months, got {horizon!r}.")


def _date(value):
    """Convert a value to a pandas Timestamp, or return None if value is None.
    
    Parameters
    ----------
    value : str, pd.Timestamp, or None
        A date value that pandas can parse.
    
    Returns
    -------
    pd.Timestamp or None
        The parsed timestamp, or None if input was None.
    """
    return None if value is None else pd.Timestamp(value)   # Return None for None input; otherwise convert to pandas Timestamp


def _filter_dates(frame, start, end, column="date"):
    """Filter a DataFrame to rows where the date column is between start and end (inclusive).
    
    Parameters
    ----------
    frame : pandas.DataFrame
        The DataFrame to filter.
    start : str, pd.Timestamp, or None
        Start date (inclusive). None means no lower bound.
    end : str, pd.Timestamp, or None
        End date (inclusive). None means no upper bound.
    column : str
        Name of the date column (default "date").
    
    Returns
    -------
    pandas.DataFrame
        The filtered DataFrame.
    """
    if start is not None:                                  # If a start date was provided
        frame = frame[frame[column] >= _date(start)]       # Keep rows where date >= start (convert start to Timestamp first)
    if end is not None:                                    # If an end date was provided
        frame = frame[frame[column] <= _date(end)]         # Keep rows where date <= end (convert end to Timestamp first)
    return frame                                           # Return the filtered DataFrame


def _category_code(item):
    """Extract the two-digit PSA category code from an item label.
    
    Parameters
    ----------
    item : str
        A full item label like "01 - FOOD AND NON-ALCOHOLIC BEVERAGES".
    
    Returns
    -------
    str
        The two-digit code, e.g. "01".
    """
    return item.split(" - ", 1)[0]                         # Split on " - " and take the first part (the code)


def _category_label(item):
    """Get the short display name for a commodity group.
    
    Looks up the short name in CATEGORY_LABELS by PSA code. If the code is
    not found, falls back to the text after " - " in the item label.
    
    Parameters
    ----------
    item : str
        A full item label like "01 - FOOD AND NON-ALCOHOLIC BEVERAGES".
    
    Returns
    -------
    str
        Short display name, e.g. "Food and non-alcoholic beverages".
    """
    # Look up the short display name by PSA code; if not found, fall back to
    # the text after " - " in the item label, capitalised.
    return CATEGORY_LABELS.get(_category_code(item), item.split(" - ", 1)[-1].capitalize())


def _rows(indicator, area=None, item=None):
    """Get all rows for an indicator, optionally filtered by area and/or item.
    
    This is the core data-fetching helper. It calls sources.price_table() to
    get the full table, then filters by area and/or item if provided.
    
    Parameters
    ----------
    indicator : str
        One of "cpi", "inflation", "purchasing_power".
    area : str or None
        Area name to filter by (e.g. "PHILIPPINES", "National Capital Region (NCR)").
    item : str or None
        Item label to filter by (e.g. "01 - FOOD AND NON-ALCOHOLIC BEVERAGES").
    
    Returns
    -------
    pandas.DataFrame
        Columns: area, area_level, item, date, value.
    
    Raises
    ------
    ValueError
        If indicator is invalid, or area/item don't exist in the data.
    """
    _check_indicator(indicator)                            # Validate the indicator name first
    table = sources.price_table(indicator)                 # Call sources.py to get the full price table (cached, from MySQL)
    if area is not None:                                   # If an area filter was provided
        rows = table[table["area"] == area]                # Filter rows where area matches
        if rows.empty:                                     # If no rows match, the area name is invalid
            raise ValueError(f"Unknown area {area!r}. See list_areas() for valid names.")
        table = rows                                       # Replace table with filtered subset
    if item is not None:                                   # If an item filter was provided
        rows = table[table["item"] == item]                # Filter rows where item matches
        if rows.empty:                                     # If no rows match, the item name is invalid
            raise ValueError(f"Unknown item {item!r}. See list_categories() for valid names.")
        table = rows                                       # Replace table with filtered subset
    return table                                           # Return the (possibly filtered) table


# --- Lists for filters -------------------------------------------------------
# These functions return lists used in dropdown/filter UI on the Streamlit pages.

def list_areas(level=None):
    """Return a list of area names, optionally filtered by area level.
    
    Parameters
    ----------
    level : str or None
        One of "national", "region", "area group", "province/city", or None
        (returns all areas).
    
    Returns
    -------
    list of str
        Area names.
    """
    if level == "region":                                  # Special case: return the 18 regions from sources.py
        return sources.regions()
    table = sources.price_table("cpi")[["area", "area_level"]].drop_duplicates()  # Get unique area/level pairs from CPI table
    if level is not None:                                  # If a level filter was provided
        if level not in set(table["area_level"]):          # Validate the level name
            raise ValueError(f"Unknown level {level!r}.")
        table = table[table["area_level"] == level]        # Filter to only that level
    return table["area"].tolist()                          # Return area names as a Python list


def list_categories(include_all_items=False):
    """Return commodity groups as a DataFrame with item, code, and label columns.
    
    Parameters
    ----------
    include_all_items : bool
        If True, include the "All items" row. Default False.
    
    Returns
    -------
    pandas.DataFrame
        Columns: item (PSA label), code (2-digit), label (short display name).
    """
    items = sorted(sources.price_table("cpi")["item"].unique())  # Get all unique item labels from CPI, sorted alphabetically
    if not include_all_items:                              # If we should exclude "All items"
        items = [i for i in items if i != ALL_ITEMS]       # Remove the all-items row from the list
    return pd.DataFrame({                                  # Build and return a DataFrame
        "item": items,                                     # Full PSA item label
        "code": [_category_code(i) for i in items],        # Extract 2-digit code for each item
        "label": ["All items" if i == ALL_ITEMS else _category_label(i) for i in items],  # Short display name for each item
    })


def get_date_range(indicator="cpi"):
    """Return the (first month, last month) available for an indicator.
    
    Parameters
    ----------
    indicator : str
        One of "cpi", "inflation", "purchasing_power".
    
    Returns
    -------
    tuple of (pd.Timestamp, pd.Timestamp)
        (earliest date, latest date) in the data.
    """
    dates = _rows(indicator)["date"]                       # Get all dates for this indicator
    return dates.min(), dates.max()                        # Return earliest and latest dates


# --- Historical series -------------------------------------------------------
# These functions return time series data (date, value) for charts and tables.

def get_series(indicator, start=None, end=None, area=NATIONAL, item=ALL_ITEMS):
    """Return one monthly time series as a DataFrame with columns: date, value.
    
    For purchasing_power, the item is always ALL_ITEMS (purchasing power has
    no commodity breakdown).
    
    Parameters
    ----------
    indicator : str
        One of "cpi", "inflation", "purchasing_power".
    start : str, pd.Timestamp, or None
        Start date (inclusive). None means no lower bound.
    end : str, pd.Timestamp, or None
        End date (inclusive). None means no upper bound.
    area : str
        Area name (default "PHILIPPINES").
    item : str
        Item label (default "0 - ALL ITEMS").
    
    Returns
    -------
    pandas.DataFrame
        Columns: date, value. Sorted by date ascending.
    """
    if indicator == "purchasing_power":                    # Purchasing power has no commodity breakdown, so force all items
        item = ALL_ITEMS
    rows = _filter_dates(_rows(indicator, area, item), start, end)  # Get rows for this indicator/area/item, filtered by date
    return rows[["date", "value"]].sort_values("date").reset_index(drop=True)  # Return only date and value columns, sorted, with clean index


def get_cpi(start=None, end=None, area=NATIONAL, item=ALL_ITEMS):
    """Return monthly CPI series (2018 = 100).
    
    Parameters
    ----------
    start, end : str or pd.Timestamp or None
        Date range filter.
    area : str
        Area name.
    item : str
        Commodity group label.
    
    Returns
    -------
    pandas.DataFrame
        Columns: date, value.
    """
    return get_series("cpi", start, end, area, item)       # Delegate to get_series with indicator="cpi"


def get_inflation(start=None, end=None, area=NATIONAL, item=ALL_ITEMS):
    """Return monthly year-on-year inflation series (%).
    
    Parameters
    ----------
    start, end : str or pd.Timestamp or None
        Date range filter.
    area : str
        Area name.
    item : str
        Commodity group label.
    
    Returns
    -------
    pandas.DataFrame
        Columns: date, value.
    """
    return get_series("inflation", start, end, area, item) # Delegate to get_series with indicator="inflation"


def get_purchasing_power(start=None, end=None, area=NATIONAL):
    """Return monthly purchasing power of the peso series.
    
    Parameters
    ----------
    start, end : str or pd.Timestamp or None
        Date range filter.
    area : str
        Area name.
    
    Returns
    -------
    pandas.DataFrame
        Columns: date, value.
    """
    return get_series("purchasing_power", start, end, area)  # Delegate to get_series with indicator="purchasing_power"


def get_series_wide(indicator, start=None, end=None, areas=None, items=None):
    """Return several series side by side for comparison charts.
    
    You can compare several areas (one item) or several items (one area),
    but not both at the same time.
    
    Parameters
    ----------
    indicator : str
        One of "cpi", "inflation", "purchasing_power".
    start, end : str or pd.Timestamp or None
        Date range filter.
    areas : list of str or None
        List of area names. Defaults to [PHILIPPINES].
    items : list of str or None
        List of item labels. Defaults to [ALL_ITEMS].
    
    Returns
    -------
    pandas.DataFrame
        Indexed by date, with one column per area or item.
    """
    areas = areas or [NATIONAL]                            # Default areas to national if none provided
    items = items or [ALL_ITEMS]                           # Default items to all-items if none provided
    if len(areas) > 1 and len(items) > 1:                  # Cannot compare multiple areas AND multiple items at once
        raise ValueError("Compare several areas or several items, not both.")
    frames = {}                                            # Dict to hold each series as a separate column
    for area in areas:                                     # Loop through each area
        for item in items:                                 # Loop through each item
            # The column key is the area when comparing areas, the item when
            # comparing items, and just the area otherwise.
            key = area if len(areas) > 1 else (item if len(items) > 1 else area)  # Choose column name: area name if comparing areas, item if comparing items
            frames[key] = get_series(indicator, start, end, area, item).set_index("date")["value"]  # Get series, set date as index, extract value column
    return pd.DataFrame(frames)                            # Combine all series into one DataFrame (dates as index, one column per area/item)


def get_period_stats(indicator, start=None, end=None, area=NATIONAL, item=ALL_ITEMS):
    """Return summary statistics for a period: highest, lowest, average, change.
    
    Parameters
    ----------
    indicator : str
        One of "cpi", "inflation", "purchasing_power".
    start, end : str or pd.Timestamp or None
        Date range filter.
    area : str
        Area name.
    item : str
        Commodity group label.
    
    Returns
    -------
    dict
        Keys: indicator, start, end, months, highest, lowest, average,
        first, last, change, percent_change.
    """
    series = get_series(indicator, start, end, area, item) # Get the time series for the period
    if series.empty:                                       # If no data in the period, raise error
        raise ValueError("No data in the selected period.")
    values = series.set_index("date")["value"]             # Set date as index, extract value column as a Series
    first, last = values.iloc[0], values.iloc[-1]          # First and last values in the period
    return {                                               # Return a dictionary with all statistics
        "indicator": indicator,                            # Which indicator
        "start": values.index[0],                          # First date
        "end": values.index[-1],                           # Last date
        "months": len(values),                             # Number of months
        "highest": {"value": values.max(), "date": values.idxmax()},  # Max value and its date
        "lowest": {"value": values.min(), "date": values.idxmin()},   # Min value and its date
        "average": values.mean(),                          # Average value
        "first": first,                                    # First value
        "last": last,                                      # Last value
        "change": round(last - first, 6),                  # Absolute change (rounded to remove floating-point noise)
        "percent_change": (last / first - 1) * 100 if first else None,  # Percent change from first to last
    }


def get_latest(area=NATIONAL):
    """Return the latest value of each indicator and its change from previous month.
    
    Used for the summary KPI cards on the Dashboard page.
    
    Parameters
    ----------
    area : str
        Area name (default "PHILIPPINES").
    
    Returns
    -------
    dict
        Keys: "cpi", "inflation", "purchasing_power". Each value is a dict
        with keys: date, value, previous, change.
    """
    out = {}                                               # Dictionary to hold results for each indicator
    for indicator in INDICATORS:                           # Loop through cpi, inflation, purchasing_power
        values = get_series(indicator, area=area).set_index("date")["value"]  # Get series, set date as index, extract values
        latest, previous = values.iloc[-1], values.iloc[-2]  # Most recent value and the one before it
        out[indicator] = {                                 # Store result for this indicator
            "date": values.index[-1],                      # Date of the latest value
            "value": latest,                               # Latest value
            "previous": previous,                          # Previous month's value
            # Rounded to remove floating-point noise (e.g. -0.10000000000000053).
            "change": round(latest - previous, 6),         # Change from previous month (rounded for clean display)
        }
    return out                                             # Return dict with all three indicators


# --- Categories ----------------------------------------------------------------
# Functions for commodity group analysis (13 PSA commodity groups).

def get_category_comparison(indicator="inflation", date=None, area=NATIONAL):
    """Return the 13 commodity groups at one month, ranked highest to lowest.
    
    Parameters
    ----------
    indicator : str
        One of "cpi", "inflation", "purchasing_power".
    date : str or pd.Timestamp or None
        The month to analyze. None means the latest available month.
    area : str
        Area name.
    
    Returns
    -------
    pandas.DataFrame
        Columns: rank, item, code, label, value.
        The frame's attrs dict contains: date, indicator, area, all_items.
    """
    rows = _rows(indicator, area)                          # Get all rows for this indicator and area
    date = _date(date) if date is not None else rows["date"].max()  # Use provided date, or the latest date in the data
    month = rows[rows["date"] == date]                     # Filter to only that month
    if month.empty:                                        # If no data for that month
        raise ValueError(f"No {indicator} data for {date:%B %Y}.")

    all_items = month.loc[month["item"] == ALL_ITEMS, "value"]  # Get the all-items value for this month
    groups = month[month["item"] != ALL_ITEMS].sort_values("value", ascending=False)  # All groups except all-items, sorted by value descending
    out = pd.DataFrame({                                   # Build output DataFrame
        "rank": range(1, len(groups) + 1),                 # Rank 1, 2, 3...
        "item": groups["item"].values,                     # Full PSA item label
        "code": [_category_code(i) for i in groups["item"]],  # 2-digit code for each group
        "label": [_category_label(i) for i in groups["item"]],  # Short display name for each group
        "value": groups["value"].values,                   # The indicator value
    })
    out.attrs.update({"date": date, "indicator": indicator, "area": area,  # Store metadata in DataFrame.attrs for downstream use
                      "all_items": all_items.iloc[0] if not all_items.empty else None})
    return out


def get_top_category(date=None, area=NATIONAL):
    """Return the commodity group with the highest year-on-year inflation.
    
    Used on the Home page for the 'biggest recent price increase' card.
    
    Parameters
    ----------
    date : str or pd.Timestamp or None
        The month to analyze.
    area : str
        Area name.
    
    Returns
    -------
    dict
        Keys: date, item, label, inflation, all_items_inflation.
    """
    ranking = get_category_comparison("inflation", date, area)  # Get commodity groups ranked by inflation
    top = ranking.iloc[0]                                  # The first row is the highest inflation group
    return {                                               # Return details about the top category
        "date": ranking.attrs["date"],                     # The month analyzed
        "item": top["item"],                               # Full PSA item label
        "label": top["label"],                             # Short display name
        "inflation": top["value"],                         # Inflation rate
        "all_items_inflation": ranking.attrs["all_items"], # All-items inflation for comparison
    }


# --- Regions ---------------------------------------------------------------------
# Functions for regional analysis (comparing areas/regions).

def get_regional_comparison(indicator="inflation", date=None, item=ALL_ITEMS, regions=None):
    """Return regions at one month, ranked highest to lowest, with difference from national.
    
    Parameters
    ----------
    indicator : str
        One of "cpi", "inflation", "purchasing_power".
    date : str or pd.Timestamp or None
        The month to analyze. None means latest.
    item : str
        Item label (default ALL_ITEMS).
    regions : list of str or None
        List of region names. None means all 18 regions.
    
    Returns
    -------
    pandas.DataFrame
        Columns: rank, region, value, difference_from_national.
        The frame's attrs dict contains: date, indicator, national.
    """
    rows = _rows(indicator, item=ALL_ITEMS if indicator == "purchasing_power" else item)  # Purchasing power only has all-items
    date = _date(date) if date is not None else rows["date"].max()  # Use provided date, or latest
    month = rows[rows["date"] == date]                     # Filter to that month
    if month.empty:                                        # No data for that month
        raise ValueError(f"No {indicator} data for {date:%B %Y}.")

    regions = regions or sources.regions()                 # Use all 18 regions if none specified
    unknown = set(regions) - set(sources.regions())        # Check for invalid region names
    if unknown:
        raise ValueError(f"Unknown region(s): {', '.join(sorted(unknown))}.")

    national = month.loc[month["area"] == NATIONAL, "value"].iloc[0]  # Get the national value for comparison
    regional = month[month["area"].isin(regions)].sort_values("value", ascending=False)  # Filter to requested regions, sort descending
    out = pd.DataFrame({                                   # Build output DataFrame
        "rank": range(1, len(regional) + 1),               # Rank numbers
        "region": regional["area"].values,                 # Region names
        "value": regional["value"].values,                 # Indicator values
        "difference_from_national": regional["value"].values - national,  # How much each region differs from national
    })
    out.attrs.update({"date": date, "indicator": indicator, "national": national})  # Store metadata
    return out


# --- FIES (household finances) ---------------------------------------------------
# Functions for Family Income and Expenditure Survey data (2023 snapshot).

def get_fies(areas=None, deciles=None, level=None):
    """Return FIES data: average income, expenditure, savings by area and income decile.
    
    Parameters
    ----------
    areas : list of str or None
        Areas to include. None means all areas.
    deciles : list of str or None
        Income deciles to include. None means all deciles.
    level : str or None
        Area level filter ("national", "region", etc.).
    
    Returns
    -------
    pandas.DataFrame
        Columns: area, area_level, decile, income, expenditure, savings, savings_rate.
    """
    table = sources.fies_table()                           # Get the full FIES table from sources.py
    if level is not None:                                  # Filter by area level if specified
        table = table[table["area_level"] == level]
    if areas is not None:                                  # Filter by specific areas if specified
        unknown = set(areas) - set(table["area"])          # Check for invalid area names
        if unknown:
            raise ValueError(f"Unknown FIES area(s): {', '.join(sorted(unknown))}.")
        table = table[table["area"].isin(areas)]
    if deciles is not None:                                # Filter by specific deciles if specified
        table = table[table["decile"].isin(deciles)]
    table = table.assign(savings_rate=table["savings"] / table["income"] * 100)  # Add savings_rate column (savings / income * 100)
    return table.sort_values(["area", "decile"]).reset_index(drop=True)  # Sort by area then decile, clean index


def get_fies_by_decile(area=NATIONAL):
    """Return one area's 11 income groups (All, then 1st-10th decile).
    
    Parameters
    ----------
    area : str
        Area name.
    
    Returns
    -------
    pandas.DataFrame
        FIES data for that area.
    """
    return get_fies(areas=[area]).reset_index(drop=True)   # Delegate to get_fies with just that area


def get_fies_by_region(decile="All Income Groups"):
    """Return the 18 regions for one income group, in PSA order.
    
    Parameters
    ----------
    decile : str
        Income decile name (default "All Income Groups").
    
    Returns
    -------
    pandas.DataFrame
        FIES data for all regions at that decile, ordered by PSA region order.
    """
    table = get_fies(level="region", deciles=[decile])     # Get region-level FIES for one decile
    order = {name: i for i, name in enumerate(sources.regions())}  # Build a mapping: region name -> PSA position
    return table.sort_values("area", key=lambda s: s.map(order)).reset_index(drop=True)  # Sort regions by PSA order


# --- Forecasts and model results -------------------------------------------------
# Functions for accessing forecast data and model evaluation metrics.

def get_final_model():
    """Return the name of the selected forecasting model.
    
    Returns
    -------
    str
        Model name (e.g. "ARIMA", "Linear Regression", "Moving Average").
    """
    return sources.model_info()["final_model"]             # Read the selected model from model_info.json via sources.py


def get_model_info():
    """Return model selection details: rule, result, data period, settings.
    
    Returns
    -------
    dict
        Contents of model_info.json.
    """
    return sources.model_info()                            # Return all model info from sources.py


def get_forecast(variable="cpi", horizon=12, model=None):
    """Return forecast data for the next `horizon` months.
    
    Parameters
    ----------
    variable : str
        One of "cpi", "inflation", "purchasing_power".
    horizon : int
        Number of months ahead (1-12).
    model : str or None
        Model name. None means use the selected model.
    
    Returns
    -------
    pandas.DataFrame
        Columns: date, step, forecast, lower, upper (95% prediction interval).
    """
    _check_indicator(variable)                             # Validate the variable name
    _check_horizon(horizon)                                # Validate the horizon (1-12)
    table = sources.forecasts_table()                      # Get the cached forecasts table from sources.py
    if model is None:                                      # If no specific model requested
        rows = table[table["is_selected"]]                 # Use only the selected model's rows
    else:                                                  # If a specific model was requested
        rows = table[table["model"] == model]              # Filter to that model
        if rows.empty:                                     # If no rows match, model name is invalid
            raise ValueError(f"Unknown model {model!r}. Choose one of: {', '.join(table['model'].unique())}.")
    rows = rows[(rows["variable"] == variable) & (rows["step"] <= horizon)]  # Filter by variable and horizon
    return rows[["date", "step", "forecast", "lower", "upper"]].sort_values("step").reset_index(drop=True)  # Return selected columns, sorted by step


def get_next_month_forecast(variable="cpi"):
    """Return the first forecast month (next month) for the Home page card.
    
    Parameters
    ----------
    variable : str
        One of "cpi", "inflation", "purchasing_power".
    
    Returns
    -------
    dict
        Keys: date, forecast, lower, upper, model.
    """
    row = get_forecast(variable, horizon=1).iloc[0]        # Get the 1-month forecast, take the first row
    return {"date": row["date"], "forecast": row["forecast"], "lower": row["lower"],
            "upper": row["upper"], "model": get_final_model()}  # Return as dict including model name


def get_model_metrics(variable=None, evaluation="pooled", period=None):
    """Return MAE, RMSE, MAPE per model for evaluation results.
    
    Parameters
    ----------
    variable : str or None
        One of "cpi", "inflation", "purchasing_power". None means all variables.
    evaluation : str
        One of "pooled", "main_test", "rolling_fold", "rolling_average".
    period : str or None
        Period label to narrow results (for main_test or rolling_fold).
    
    Returns
    -------
    pandas.DataFrame
        Columns: model, variable, period, mae, rmse, mape, n_months,
        is_selected_model, in_proposal.
    """
    if evaluation not in EVALUATIONS:                      # Validate evaluation type
        raise ValueError(f"Unknown evaluation {evaluation!r}. Choose one of: {', '.join(EVALUATIONS)}.")
    table = sources.metrics_table()                        # Get cached metrics table from sources.py
    rows = table[table["evaluation"] == evaluation]        # Filter by evaluation type
    if variable is not None:                               # Filter by variable if specified
        _check_indicator(variable)
        rows = rows[rows["variable"] == variable]
    if period is not None:                                 # Filter by period if specified
        rows = rows[rows["period"] == period]
        if rows.empty:                                     # Invalid period name
            raise ValueError(f"Unknown period {period!r} for evaluation {evaluation!r}.")
    eligible = set(sources.model_info()["selection"]["eligible_models"])  # Get list of models eligible for selection
    rows = rows.assign(in_proposal=rows["model"].isin(eligible))  # Add column: is this model in the proposal?
    return rows[["model", "variable", "period", "mae", "rmse", "mape", "n_months",
                 "is_selected_model", "in_proposal"]].reset_index(drop=True)  # Return selected columns


def get_test_predictions(variable="cpi", evaluation="main_test", model=None):
    """Return forecast predictions made during evaluation, with actual values.
    
    Used for actual-vs-forecast comparison charts.
    
    Parameters
    ----------
    variable : str
        One of "cpi", "inflation", "purchasing_power".
    evaluation : str
        One of "main_test" or "rolling_origin".
    model : str or None
        Model name. None means all models.
    
    Returns
    -------
    pandas.DataFrame
        Columns: origin, model, date, step, forecast, lower, upper, actual, error.
    """
    _check_indicator(variable)                             # Validate variable
    if evaluation not in ("main_test", "rolling_origin"):  # Validate evaluation type
        raise ValueError("evaluation must be 'main_test' or 'rolling_origin'.")
    table = sources.test_predictions_table()               # Get cached test predictions from sources.py
    rows = table[(table["evaluation"] == evaluation) & (table["variable"] == variable)]  # Filter by evaluation and variable
    if model is not None:                                  # Filter by model if specified
        rows = rows[rows["model"] == model]
    return rows[["origin", "model", "date", "step", "forecast", "lower", "upper", "actual", "error"]].reset_index(drop=True)  # Return selected columns


def get_error_by_step(variable="cpi", model=None):
    """Return mean absolute error at each step ahead (1-12 months).
    
    Parameters
    ----------
    variable : str
        One of "cpi", "inflation", "purchasing_power".
    model : str or None
        Model name. None means all models.
    
    Returns
    -------
    pandas.DataFrame
        Columns: model, step, mae.
    """
    _check_indicator(variable)                             # Validate variable
    table = sources.error_by_step_table()                  # Get cached error-by-step data from sources.py
    rows = table[table["variable"] == variable]            # Filter by variable
    if model is not None:                                  # Filter by model if specified
        rows = rows[rows["model"] == model]
    return rows[["model", "step", "mae"]].reset_index(drop=True)  # Return selected columns
