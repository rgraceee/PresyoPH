"""Derive inflation and purchasing power from CPI (option B).

Only CPI is forecast. Forecasted inflation and purchasing power are computed
from the CPI forecast with the same formulas PSA uses:

    inflation (%)       = (CPI_t / CPI_{t-12} - 1) * 100, rounded to 1 decimal
    purchasing power    = 100 / CPI_t, rounded to 2 decimals

Both formulas reproduce PSA's published national series exactly for every
released month.
"""

import pandas as pd


def to_inflation(cpi, rounded=True):
    """Year-on-year inflation in percent from a monthly CPI series.

    The first 12 months are dropped because they have no prior-year value.
    To derive inflation for forecast months, pass the actual history joined
    with the forecast so that CPI_{t-12} is available.
    """
    inflation = (cpi / cpi.shift(12) - 1) * 100
    inflation = inflation.dropna()
    if rounded:
        inflation = inflation.round(1)
    inflation.name = "inflation"
    return inflation


def to_purchasing_power(cpi, rounded=True):
    """Purchasing power of the peso (base 2018=100) from a monthly CPI series."""
    purchasing_power = 100 / cpi
    if rounded:
        purchasing_power = purchasing_power.round(2)
    purchasing_power.name = "purchasing_power"
    return purchasing_power


def derive_intervals(cpi_history, cpi_lower, cpi_upper, rounded=True):
    """Prediction intervals for inflation and purchasing power from the CPI
    interval.

    Both formulas are monotonic in CPI_t (CPI_{t-12} is actual data for
    horizons up to 12 months), so the CPI bounds map directly onto the derived
    bounds. Purchasing power falls as CPI rises, so its bounds swap.
    """
    combined_lower = pd.concat([cpi_history, cpi_lower])
    combined_upper = pd.concat([cpi_history, cpi_upper])
    out = pd.DataFrame(index=cpi_lower.index)
    out["inflation_lower"] = to_inflation(combined_lower, rounded).reindex(cpi_lower.index)
    out["inflation_upper"] = to_inflation(combined_upper, rounded).reindex(cpi_upper.index)
    out["purchasing_power_lower"] = to_purchasing_power(cpi_upper, rounded)
    out["purchasing_power_upper"] = to_purchasing_power(cpi_lower, rounded)
    return out


def derive_all(cpi_history, cpi_forecast, rounded=True):
    """Inflation and purchasing power for the forecast months.

    cpi_history holds actual CPI up to the forecast origin; cpi_forecast holds
    the forecasted CPI after it. Returns a DataFrame indexed like cpi_forecast
    with columns cpi, inflation and purchasing_power.
    """
    combined = pd.concat([cpi_history, cpi_forecast])
    out = pd.DataFrame({"cpi": cpi_forecast})
    out["inflation"] = to_inflation(combined, rounded).reindex(cpi_forecast.index)
    out["purchasing_power"] = to_purchasing_power(cpi_forecast, rounded)
    return out
