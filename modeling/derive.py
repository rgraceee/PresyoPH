"""
================================================================================
FILE: modeling/derive.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
This file derives inflation and purchasing power from CPI forecasts (option B).
Only CPI is directly forecast by the statistical models. Inflation and
purchasing power are then computed from the CPI forecast using the same
formulas PSA uses:

    inflation (%)       = (CPI_t / CPI_{t-12} - 1) * 100, rounded to 1 decimal
    purchasing power    = 100 / CPI_t, rounded to 2 decimals

Both formulas reproduce PSA's published national series exactly for every
released month, so the derived forecasts are consistent with PSA's methodology.

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- modeling/evaluation.py: Imports derive_all(), derive_intervals() for scoring
  inflation and purchasing power forecasts.
- modeling/run_pipeline.py: Does NOT import derive directly (evaluation.py does).
- backend/data.py: Does NOT import derive (derivation happens in modeling, not
  in the data access layer).
- app/pages/*: Do NOT import derive (derived values are pre-computed in the
  forecasting pipeline and stored in datasets/outputs/).

================================================================================
"""

"""Derive inflation and purchasing power from CPI (option B).

Only CPI is forecast. Forecasted inflation and purchasing power are computed
from the CPI forecast with the same formulas PSA uses:

    inflation (%)       = (CPI_t / CPI_{t-12} - 1) * 100, rounded to 1 decimal
    purchasing power    = 100 / CPI_t, rounded to 2 decimals

Both formulas reproduce PSA's published national series exactly for every
released month.
"""

import pandas as pd                                  # pandas: Series and DataFrame operations


def to_inflation(cpi, rounded=True):
    """Convert a monthly CPI series to year-on-year inflation in percent.
    
    Formula: inflation_t = (CPI_t / CPI_{t-12} - 1) * 100
    
    The first 12 months are dropped because they have no prior-year value.
    To derive inflation for forecast months, pass the actual history joined
    with the forecast so that CPI_{t-12} is available.
    
    Parameters
    ----------
    cpi : pandas.Series
        Monthly CPI values indexed by date.
    rounded : bool
        If True, round to 1 decimal place.
    
    Returns
    -------
    pandas.Series
        Inflation values indexed by date (first 12 months dropped).
    """
    inflation = (cpi / cpi.shift(12) - 1) * 100        # Year-on-year percent change
    inflation = inflation.dropna()                     # Drop first 12 months (no prior-year value)
    if rounded:
        inflation = inflation.round(1)                 # Round to 1 decimal (PSA convention)
    inflation.name = "inflation"                       # Name the series
    return inflation


def to_purchasing_power(cpi, rounded=True):
    """Convert a monthly CPI series to purchasing power of the peso.
    
    Formula: purchasing_power_t = 100 / CPI_t
    
    Base year 2018 = 100, so purchasing power starts at 1.00 and falls as
    prices rise.
    
    Parameters
    ----------
    cpi : pandas.Series
        Monthly CPI values indexed by date.
    rounded : bool
        If True, round to 2 decimal places.
    
    Returns
    -------
    pandas.Series
        Purchasing power values indexed by date.
    """
    purchasing_power = 100 / cpi                       # Reciprocal of CPI, scaled to base 100
    if rounded:
        purchasing_power = purchasing_power.round(2)   # Round to 2 decimals (PSA convention)
    purchasing_power.name = "purchasing_power"         # Name the series
    return purchasing_power


def derive_intervals(cpi_history, cpi_lower, cpi_upper, rounded=True):
    """Derive prediction intervals for inflation and purchasing power from CPI intervals.
    
    Both formulas are monotonic in CPI_t (CPI_{t-12} is actual data for
    horizons up to 12 months), so the CPI bounds map directly onto the derived
    bounds. Purchasing power falls as CPI rises, so its bounds swap:
    - inflation_lower comes from cpi_lower
    - inflation_upper comes from cpi_upper
    - purchasing_power_lower comes from cpi_upper (higher CPI = lower purchasing power)
    - purchasing_power_upper comes from cpi_lower
    
    Parameters
    ----------
    cpi_history : pandas.Series
        Actual CPI history up to the forecast origin.
    cpi_lower : pandas.Series
        Lower bound of CPI prediction interval for forecast months.
    cpi_upper : pandas.Series
        Upper bound of CPI prediction interval for forecast months.
    rounded : bool
        If True, round to appropriate decimal places.
    
    Returns
    -------
    pandas.DataFrame
        Columns: inflation_lower, inflation_upper, purchasing_power_lower,
        purchasing_power_upper. Indexed like cpi_lower.
    """
    combined_lower = pd.concat([cpi_history, cpi_lower])  # History + lower bound for shift(12) to work
    combined_upper = pd.concat([cpi_history, cpi_upper])  # History + upper bound
    out = pd.DataFrame(index=cpi_lower.index)
    out["inflation_lower"] = to_inflation(combined_lower, rounded).reindex(cpi_lower.index)
    out["inflation_upper"] = to_inflation(combined_upper, rounded).reindex(cpi_upper.index)
    out["purchasing_power_lower"] = to_purchasing_power(cpi_upper, rounded)  # Swapped: upper CPI = lower PP
    out["purchasing_power_upper"] = to_purchasing_power(cpi_lower, rounded)  # Swapped: lower CPI = upper PP
    return out


def derive_all(cpi_history, cpi_forecast, rounded=True):
    """Derive inflation and purchasing power for the forecast months.
    
    Combines actual history with forecasted CPI, then applies the derivation
    formulas to get all three variables for the forecast period.
    
    Parameters
    ----------
    cpi_history : pandas.Series
        Actual CPI up to the forecast origin.
    cpi_forecast : pandas.Series
        Forecasted CPI after the origin.
    rounded : bool
        If True, round to appropriate decimal places.
    
    Returns
    -------
    pandas.DataFrame
        Indexed like cpi_forecast with columns: cpi, inflation, purchasing_power.
    """
    combined = pd.concat([cpi_history, cpi_forecast])   # History + forecast for shift(12)
    out = pd.DataFrame({"cpi": cpi_forecast})           # Start with forecasted CPI
    out["inflation"] = to_inflation(combined, rounded).reindex(cpi_forecast.index)
    out["purchasing_power"] = to_purchasing_power(cpi_forecast, rounded)
    return out
