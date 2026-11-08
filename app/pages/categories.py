"""
================================================================================
FILE: app/pages/categories.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
Screen 3: Household Necessities. Shows price trends and comparisons across the
13 PSA commodity groups. Users can select a category and time period, view
its trend vs. the all-items average, see a comparison of all categories, and
find the fastest-rising categories.

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- app/streamlit_app.py: Registers this page as "categories".
- backend/data.py: Calls data.list_categories(), data.get_series(), data.get_category_comparison().
- app/ui/shell.py: Calls shell.page_header(), shell.chip(), shell.panel_header(),
  shell.filter_stat(), shell.ranked_list(), shell.esc().
- app/ui/layout.py: Calls month_label().
- app/ui/charts.py: Calls charts.ranked_bar_figure(), charts.LAYOUT.
- app/ui/queries.py: Calls queries.get_category_changes().
- app/ui/tokens.py: Does NOT import tokens directly here.

================================================================================
"""

"""Screen 3: Household Necessities (Figma: Household Necessities Category Analysis)."""

import pandas as pd                                   # pandas: DataFrame operations
import plotly.graph_objects as go                     # plotly: chart library
import streamlit as st                                # streamlit: UI components

from app.ui import queries, shell, tokens             # shell: UI components; queries: category changes
from app.ui.charts import LAYOUT                      # LAYOUT: default Plotly layout
from app.ui.layout import month_label                 # month_label: format dates
from backend import data                              # backend: data access functions

# Period options for the category trend chart.
PERIODS = {"6 months": 6, "12 months": 12, "24 months": 24, "All (since 2018)": None}
# Colours for the comparison bars table (one per row, cycled if more than 6).
BAR_COLORS = ["#1B5E4B", "#E9AA2B", "#EE7B30", "#D94B3D", "#6FA06B", "#8FA79A"]


def category_trend_figure(series, average, name):
    """Build a line chart comparing one category's CPI to the all-items average.
    
    Parameters
    ----------
    series : pandas.DataFrame
        Columns: date, value for the selected category.
    average : pandas.DataFrame
        Columns: date, value for all items.
    name : str
        Category name for the legend.
    
    Returns
    -------
    plotly.graph_objects.Figure
    """
    fig = go.Figure()
    # Selected category: filled area line
    fig.add_trace(go.Scatter(x=series["date"], y=series["value"], mode="lines+markers", name=name, fill="tozeroy",
                             line=dict(color=tokens.INDICATOR_COLORS["cpi"], width=3), fillcolor="rgba(27,94,75,0.07)",
                             hovertemplate="%{y:.1f}<extra>" + name + "</extra>"))
    # All-items average: dashed grey line
    fig.add_trace(go.Scatter(x=average["date"], y=average["value"], mode="lines", name="All categories average",
                             line=dict(color="#9CA3AF", width=2, dash="dash"), hovertemplate="%{y:.1f}<extra>All items</extra>"))
    low = min(series["value"].min(), average["value"].min())  # Lowest value for y-axis range
    fig.update_layout(**LAYOUT, height=380, yaxis=dict(title="Price index (2018 = 100)", range=[low * 0.92, series["value"].max() * 1.06],
                                                         gridcolor="#e8e8de"))
    return fig


def comparison_bars(ranking, selected_label):
    """Render an HTML table with bar visuals showing each category's CPI.
    
    Parameters
    ----------
    ranking : pandas.DataFrame
        Category ranking output from data.get_category_comparison().
    selected_label : str
        The currently selected category label (shown in bold).
    """
    values = ranking["value"]
    scale = values.max()                                  # For bar width percentages
    rows = []
    for i, r in ranking.reset_index(drop=True).iterrows():
        color = BAR_COLORS[min(i, len(BAR_COLORS) - 1)]   # Cycle through colours
        bold = "font-weight:800" if r["label"] == selected_label else ""  # Bold the selected row
        rows.append(f'<tr><td style="font-size:11.5px;width:42%;{bold}">{shell.esc(r["label"])}</td>'
                    f'<td><div class="pp-bar"><i style="width:{r["value"] / scale * 100:.1f}%;background:{color}"></i></div></td>'
                    f'<td class="num" style="font-weight:700;width:48px">{r["value"]:.1f}</td></tr>')
    st.markdown(f'<table class="pp-tbl">{"".join(rows)}</table>', unsafe_allow_html=True)


def render():
    """Render the Household Necessities page."""
    shell.page_header("Household Necessities Category Analysis",
                      "Compare price movements across the essential categories that shape Filipino household expenses.",
                      shell.chip("Updated " + month_label(data.get_date_range("cpi")[1])))

    # Get all commodity groups
    categories = data.list_categories()
    labels = list(categories["label"])
    items = categories.set_index("label")["item"]         # Map label -> PSA item code
    # Restore selected category from session state (set by search)
    if st.session_state.get("cat_select") not in labels:
        st.session_state["cat_select"] = labels[0]

    with st.container(key="filter_cats"):                 # Filter controls
        c1, c2, c3 = st.columns([1.5, 1.2, 1.5], vertical_alignment="center")
        label = c1.selectbox("Necessity Category", labels, key="cat_select")
        period = c2.selectbox("Period", list(PERIODS), key="cat_period")
        first, last = data.get_date_range("cpi")
        start = first if PERIODS[period] is None else last - pd.DateOffset(months=PERIODS[period] - 1)
        series = data.get_series("cpi", start, None, item=items[label])  # Selected category's CPI
        average = data.get_series("cpi", start, None)     # All-items average CPI
        change = (series["value"].iloc[-1] / series["value"].iloc[0] - 1) * 100  # Percent change over period
        with c3:
            shell.filter_stat("Current Category Index", f"{series['value'].iloc[-1]:.1f}",
                              f"{'▲' if change >= 0 else '▼'} {abs(change):.1f}% vs. start of period",
                              tone="dn" if change > 0 else "up")

    with st.container(key="card_cat_trend"):              # Trend chart card
        shell.panel_header("Category Price Trend", f"Price index movement for {label.lower()}", right=period)
        st.plotly_chart(category_trend_figure(series, average, label), config={"displayModeBar": False})

    # Toggle to show all 13 categories or just top 6
    show_all = st.toggle("Show all 13 categories", key="cat_all",
                         help="The Figma design lists six; PSA publishes thirteen commodity groups.")
    ranking = data.get_category_comparison("cpi")         # All categories ranked by current CPI
    if not show_all:
        top = ranking.head(6)                             # Top 6 by CPI value
        # Show top 6 plus the selected category if it's not in top 6
        ranking_view = top if label in set(top["label"]) else ranking[ranking["label"].isin(set(top["label"]) | {label})]
    else:
        ranking_view = ranking
    compare, rank = st.columns(2)
    with compare:
        with st.container(key="card_cat_compare"):
            shell.panel_header("Category Comparison", f"Current index, {month_label(ranking.attrs['date'])}", right="Price index")
            comparison_bars(ranking_view, label)          # HTML table with bar visuals
    with rank:
        # Fastest-rising categories over the selected period
        changes = queries.get_category_changes(max(1, len(series) - 1))
        with st.container(key="card_cat_rank"):
            shell.panel_header("Fastest-Rising Categories", "Ranked by change in the selected period", right="Change")
            shell.ranked_list([{"rank": r["rank"], "name": r["label"], "sub": "Household necessity", "change": r["change_pct"]}
                               for _, r in (changes if show_all else changes.head(6)).iterrows()])
    st.caption("Categories are PSA's 13 commodity groups. Item-level prices (such as rice or cooking oil) are not part of "
               "the datasets used by PresyoPH.")


render()                                                 # Execute the page when Streamlit loads it
