"""
================================================================================
FILE: app/ui/layout.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
This file contains shared "page furniture" used by every screen:

  - month_options(): list of all months for a dropdown
  - month_label(): format a date as "Aug 2026"
  - area_options(): list of areas (national, area group, regions) for dropdowns
  - area_label(): display-friendly area name ("Philippines (national)" vs "PHILIPPINES")
  - footer(): PSA attribution + forecast disclaimer at the bottom of every page

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- app/pages/trends.py: Calls month_options(), month_label(), area_options(), area_label().
- app/pages/finances.py: Calls area_label(), area_options(), month_label().
- app/pages/regional.py: Calls month_label(), month_options().
- app/pages/reports.py: Calls month_label(), month_options(), area_label(), area_options().
- app/pages/data_explorer.py: Calls month_label(), month_options(), area_label(), area_options().
- backend/data.py: Calls data.get_date_range(), data.NATIONAL, data.list_areas().
- app/ui/tokens.py: Uses tokens.PSA_ATTRIBUTION, tokens.FORECAST_DISCLAIMER.

================================================================================
"""

"""Page furniture shared by every screen: month pickers, the footer."""

import pandas as pd                                  # pandas: date range generation
import streamlit as st                               # streamlit: divider and caption components

from app.ui import tokens                            # tokens: PSA attribution and forecast disclaimer text
from backend import data                             # backend data access (date ranges, area lists)


def month_options(indicator="cpi"):
    """Return a list of all months available for an indicator, oldest first.
    
    Used to populate month dropdowns on trends, regional, and other pages.
    
    Parameters
    ----------
    indicator : str
        One of "cpi", "inflation", "purchasing_power".
    
    Returns
    -------
    list of pandas.Timestamp
        All month-start dates from the first to the last available month.
    """
    first, last = data.get_date_range(indicator)       # Get earliest and latest dates for this indicator
    return list(pd.date_range(first, last, freq="MS")) # Generate all month-starts between them


def month_label(value):
    """Format a date as a short month label (e.g. "Aug 2026").
    
    Parameters
    ----------
    value : pandas.Timestamp or datetime
        The date to format.
    
    Returns
    -------
    str
        Formatted label like "Aug 2026".
    """
    return f"{value:%b %Y}"                            # %b = abbreviated month name, %Y = 4-digit year


def area_options():
    """Return area options for dropdowns: national, then area group, then regions.
    
    Returns
    -------
    list of str
        Area names starting with "PHILIPPINES", then "Areas Outside NCR",
        then the 18 regions.
    """
    return [data.NATIONAL] + data.list_areas("area group") + data.list_areas("region")


def area_label(name):
    """Return a display-friendly version of an area name.
    
    "PHILIPPINES" becomes "Philippines (national)"; other names are returned as-is.
    
    Parameters
    ----------
    name : str
        Raw area name from the data.
    
    Returns
    -------
    str
        Display-friendly area name.
    """
    return "Philippines (national)" if name == data.NATIONAL else name


def footer():
    """Render the page footer: PSA attribution and forecast disclaimer.
    
    Shown at the bottom of every dashboard page.
    """
    st.divider()                                         # Horizontal line separator
    st.caption(f"{tokens.PSA_ATTRIBUTION}  \n**Forecast disclaimer:** {tokens.FORECAST_DISCLAIMER}")
    # Shows source attribution and the disclaimer that forecasts are statistical estimates only
