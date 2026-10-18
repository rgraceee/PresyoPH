"""Page furniture shared by every screen: month pickers, the footer."""

import pandas as pd
import streamlit as st

from app.ui import tokens
from backend import data


def month_options(indicator="cpi"):
    """All months available for an indicator, oldest first."""
    first, last = data.get_date_range(indicator)
    return list(pd.date_range(first, last, freq="MS"))


def month_label(value):
    return f"{value:%b %Y}"


def area_options():
    """National, then the area group, then the 18 regions."""
    return [data.NATIONAL] + data.list_areas("area group") + data.list_areas("region")


def area_label(name):
    return "Philippines (national)" if name == data.NATIONAL else name


def footer():
    """PSA attribution and the forecast disclaimer, shown under every page."""
    st.divider()
    st.caption(f"{tokens.PSA_ATTRIBUTION}  \n**Forecast disclaimer:** {tokens.FORECAST_DISCLAIMER}")
