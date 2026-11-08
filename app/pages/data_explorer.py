"""
================================================================================
FILE: app/pages/data_explorer.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
Supporting page: Data Explorer. Lets users browse the raw data behind the
charts and download it as CSV. Two dataset types:

  - Price data (CPI, inflation, purchasing power): filterable by date range,
    area, and category
  - FIES data (2023 snapshot): filterable by area and income decile

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- app/streamlit_app.py: Registers this page as "explorer".
- backend/data.py: Calls data.NATIONAL, data.list_areas(), data.get_fies(),
  data.ALL_ITEMS.
- app/ui/shell.py: Calls shell.page_header(), shell.pill().
- app/ui/layout.py: Calls area_label(), area_options(), month_label(), month_options().
- app/ui/queries.py: Calls queries.get_table().
- app/ui/tokens.py: Calls tokens.DECILE_SHORT, tokens.DECILE_LONG, tokens.FIES_NOTE.

================================================================================
"""

"""Supporting page: Data Explorer. Filterable tables with CSV download."""

import streamlit as st                                # streamlit: UI components

from app.ui import queries, shell, tokens             # shell: UI components; queries: data table builder; tokens: FIES labels
from app.ui.layout import area_label, area_options, month_label, month_options  # UI helpers
from backend import data                              # backend: data access functions

# Dataset options for the dropdown: key -> display name.
DATASETS = {
    "cpi": "Consumer Price Index (CPI)",
    "inflation": "Inflation rate",
    "purchasing_power": "Purchasing power of the peso",
    "fies": "Household income, spending, savings (FIES 2023)",
}


def price_table(indicator):
    """Show filter controls and return a filtered price table for one indicator.
    
    Parameters
    ----------
    indicator : str
        One of "cpi", "inflation", "purchasing_power".
    
    Returns
    -------
    pandas.DataFrame
        The filtered long table.
    """
    months = month_options(indicator)                  # All available months
    start, end = st.select_slider("Date range", options=months, value=(months[0], months[-1]), format_func=month_label)
    areas = st.multiselect("Areas", area_options(), default=[data.NATIONAL], format_func=area_label)
    items = None
    if indicator != "purchasing_power":                # Purchasing power has no categories
        categories = data.list_categories(include_all_items=True)
        chosen = st.multiselect("Categories", list(categories["label"]), default=["All items"])
        items = list(categories.set_index("label").loc[chosen, "item"])  # Map labels to PSA item codes
    return queries.get_table(indicator, start, end, areas or None, items if items else None)


def fies_table():
    """Show filter controls and return a filtered FIES table.
    
    Returns
    -------
    pandas.DataFrame
        The filtered FIES table with renamed columns.
    """
    areas = st.multiselect("Areas", [data.NATIONAL] + data.list_areas("region"), default=[data.NATIONAL],
                           format_func=area_label)
    groups = st.multiselect("Income levels", list(tokens.DECILE_SHORT), default=list(tokens.DECILE_SHORT),
                            format_func=tokens.DECILE_LONG.get)
    st.info(tokens.FIES_NOTE, icon=":material/info:")  # Note about FIES being a 2023 snapshot
    table = data.get_fies(areas=areas or None, deciles=groups or None)
    return table.drop(columns=["area_level"]).rename(columns={  # Rename columns for clarity
        "income": "income_thousand_pesos", "expenditure": "expenditure_thousand_pesos",
        "savings": "savings_thousand_pesos", "savings_rate": "savings_rate_percent"})


def render():
    """Render the Data Explorer page."""
    shell.page_header("Data Explorer", "Browse the data behind the charts and download it as CSV.",
                      shell.pill("Public PSA statistics, no personal data", dot=True))
    with st.container(key="filter_explorer"):            # Dataset selector
        key = st.selectbox("Dataset", list(DATASETS), format_func=DATASETS.get)
        table = fies_table() if key == "fies" else price_table(key)

    st.write(f"**{len(table):,} rows**")                # Show row count
    st.dataframe(table, hide_index=True, height=420)   # Display the table
    # Download button
    st.download_button("Download CSV", table.to_csv(index=False).encode("utf-8"),
                       file_name=f"presyoph_{key}.csv", mime="text/csv", icon=":material/download:")


render()                                               # Execute the page when Streamlit loads it
