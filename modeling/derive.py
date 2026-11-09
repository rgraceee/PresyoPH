"""Derive inflation and purchasing power from CPI forecasts."""

import pandas as pd


def to_inflation(cpi, rounded=True):
    inflation = (cpi / cpi.shift(12) - 1) * 100
    inflation = inflation.dropna()
    if rounded:
        inflation = inflation.round(1)
    inflation.name = "inflation"
    return inflation


def to_purchasing_power(cpi, rounded=True):
    purchasing_power = 100 / cpi
    if rounded:
        purchasing_power = purchasing_power.round(2)
    purchasing_power.name = "purchasing_power"
    return purchasing_power


def derive_intervals(cpi_history, cpi_lower, cpi_upper, rounded=True):
    combined_lower = pd.concat([cpi_history, cpi_lower])
    combined_upper = pd.concat([cpi_history, cpi_upper])
    out = pd.DataFrame(index=cpi_lower.index)
    out["inflation_lower"] = to_inflation(combined_lower, rounded).reindex(cpi_lower.index)
    out["inflation_upper"] = to_inflation(combined_upper, rounded).reindex(cpi_upper.index)
    out["purchasing_power_lower"] = to_purchasing_power(cpi_upper, rounded)
    out["purchasing_power_upper"] = to_purchasing_power(cpi_lower, rounded)
    return out


def derive_all(cpi_history, cpi_forecast, rounded=True):
    combined = pd.concat([cpi_history, cpi_forecast])
    out = pd.DataFrame({"cpi": cpi_forecast})
    out["inflation"] = to_inflation(combined, rounded).reindex(cpi_forecast.index)
    out["purchasing_power"] = to_purchasing_power(cpi_forecast, rounded)
    return out
