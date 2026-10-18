"""Supporting page: Data Explorer. Filterable tables with CSV download."""

import streamlit as st

from app.ui import queries, shell, tokens
from app.ui.layout import area_label, area_options, month_label, month_options
from backend import data

DATASETS = {
    "cpi": "Consumer Price Index (CPI)",
    "inflation": "Inflation rate",
    "purchasing_power": "Purchasing power of the peso",
    "fies": "Household income, spending, savings (FIES 2023)",
}


def price_table(indicator):
    months = month_options(indicator)
    start, end = st.select_slider("Date range", options=months, value=(months[0], months[-1]), format_func=month_label)
    areas = st.multiselect("Areas", area_options(), default=[data.NATIONAL], format_func=area_label)
    items = None
    if indicator != "purchasing_power":
        categories = data.list_categories(include_all_items=True)
        chosen = st.multiselect("Categories", list(categories["label"]), default=["All items"])
        items = list(categories.set_index("label").loc[chosen, "item"])
    return queries.get_table(indicator, start, end, areas or None, items if items else None)


def fies_table():
    areas = st.multiselect("Areas", [data.NATIONAL] + data.list_areas("region"), default=[data.NATIONAL],
                           format_func=area_label)
    groups = st.multiselect("Income groups", list(tokens.DECILE_SHORT), default=list(tokens.DECILE_SHORT),
                            format_func=tokens.DECILE_SHORT.get)
    st.info(tokens.FIES_NOTE, icon=":material/info:")
    table = data.get_fies(areas=areas or None, deciles=groups or None)
    return table.drop(columns=["area_level"]).rename(columns={
        "income": "income_thousand_pesos", "expenditure": "expenditure_thousand_pesos",
        "savings": "savings_thousand_pesos", "savings_rate": "savings_rate_percent"})


def render():
    shell.page_header("Data Explorer", "Browse the data behind the charts and download it as CSV.",
                      shell.pill("Public PSA statistics, no personal data", dot=True))
    with st.container(key="filter_explorer"):
        key = st.selectbox("Dataset", list(DATASETS), format_func=DATASETS.get)
        table = fies_table() if key == "fies" else price_table(key)

    st.write(f"**{len(table):,} rows**")
    st.dataframe(table, hide_index=True, height=420)
    st.download_button("Download CSV", table.to_csv(index=False).encode("utf-8"),
                       file_name=f"presyoph_{key}.csv", mime="text/csv", icon=":material/download:")


render()
