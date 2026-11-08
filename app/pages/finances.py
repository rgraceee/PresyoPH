"""
================================================================================
FILE: app/pages/finances.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
Screen 4: Purchasing Power and Household Finances. Shows:

  - Purchasing power of the peso over time (monthly or annual view)
  - FIES 2023 household income, spending, and savings by income decile
  - Grouped bar chart comparing all three measures across deciles
  - Financial insight text

Purchasing power is a monthly series. FIES is a 2023 snapshot -- they are
shown together but are not the same data.

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- app/streamlit_app.py: Registers this page as "finances".
- backend/data.py: Calls data.get_purchasing_power(), data.get_fies_by_decile(),
  data.NATIONAL, data.list_areas(), data.list_areas("region").
- app/ui/shell.py: Calls shell.page_header(), shell.pill(), shell.filter_title(),
  shell.filter_stat(), shell.mini_card(), shell.insight_card(), shell.panel_header().
- app/ui/layout.py: Calls area_label(), area_options(), month_label().
- app/ui/charts.py: Calls charts.grouped_bar_figure(), charts.LAYOUT.
- app/ui/tokens.py: Calls tokens.DECILE_SHORT, tokens.DECILE_LONG, tokens.FIES_COLORS,
  tokens.INCOME_RANK_AXIS, tokens.FIES_NOTE.
- backend/data.py: Calls data.get_purchasing_power(), data.get_fies_by_decile().

================================================================================
"""

"""Screen 4: Purchasing Power and Household Finances (Figma: Purchasing Power and Household Financial Analysis).

Purchasing power is a monthly series (national and regional). FIES is a 2023
snapshot by income group; the two are shown together but are not the same data.
"""

import plotly.graph_objects as go                     # plotly: chart library
import streamlit as st                                # streamlit: UI components

from app.ui import charts, shell, tokens              # shell: UI components; charts: Plotly figures; tokens: FIES styling
from app.ui.charts import LAYOUT                      # LAYOUT: default Plotly layout
from app.ui.layout import area_label, area_options, month_label  # UI helpers
from backend import data                              # backend: data access functions

# FIES measure names mapped to display labels.
MEASURES = {"income": "Income", "expenditure": "Spending", "savings": "Savings"}


def trend_figure(series, label):
    """Build a line chart of purchasing power over time with a ₱1.00 reference line.
    
    Parameters
    ----------
    series : pandas.DataFrame
        Columns: date, value.
    label : str
        Series name for the legend.
    
    Returns
    -------
    plotly.graph_objects.Figure
    """
    fig = go.Figure()
    # Purchasing power line (filled area)
    fig.add_trace(go.Scatter(x=series["date"], y=series["value"], mode="lines+markers", name=label, fill="tozeroy",
                             line=dict(color=tokens.INDICATOR_COLORS["inflation"], width=3), marker=dict(size=5),
                             fillcolor="rgba(233,170,43,0.10)", hovertemplate="%{y:.2f}<extra>" + label + "</extra>"))
    # Reference line at ₱1.00 (2018 baseline)
    fig.add_hline(y=1.0, line_dash="dot", line_color="#9CA3AF", annotation_text="2018 purchasing power (₱1.00)",
                  annotation_position="top right")
    fig.update_layout(**LAYOUT, height=355, showlegend=False,
                      yaxis=dict(title="Purchasing power (2018 = ₱1.00)", range=[max(0, series["value"].min() * 0.85), 1.1],
                                 gridcolor="#e8e8de"))
    return fig


def group_bars(groups, selected):
    """Build grouped bars of income, spending, and savings by income decile.
    
    Parameters
    ----------
    groups : pandas.DataFrame
        FIES data for one area, one row per decile.
    selected : str
        The selected decile (highlighted with a background band).
    
    Returns
    -------
    plotly.graph_objects.Figure
    """
    labels = [tokens.DECILE_SHORT[d] for d in groups["decile"]]  # Short decile names for x-axis
    fig = charts.grouped_bar_figure(labels, {MEASURES[m]: groups[m] for m in MEASURES},
                                    {MEASURES[m]: tokens.FIES_COLORS[m] for m in MEASURES}, y_title="Thousand pesos per family",
                                    height=360)
    fig.update_xaxes(title=tokens.INCOME_RANK_AXIS)
    # Highlight the selected decile with a background band
    if selected in set(groups["decile"]):
        fig.add_vrect(x0=list(groups["decile"]).index(selected) - 0.5, x1=list(groups["decile"]).index(selected) + 0.5,
                      fillcolor="rgba(27,94,75,0.08)", line_width=0)
    return fig


def render():
    """Render the Purchasing Power and Household Finances page."""
    shell.page_header("Purchasing Power and Household Financial Analysis",
                      "Understand how household income, spending, and savings relate to the peso's purchasing power.",
                      shell.pill("Financial data based on the 2023 FIES snapshot", tone="gold"))

    # Filter controls: income level, area, view type
    areas = [data.NATIONAL] + data.list_areas("region")   # National + all regions
    fies_groups = [d for d in tokens.DECILE_SHORT]          # All decile names
    with st.container(key="filter_pp"):
        c1, c2, c3, c4 = st.columns([1.4, 1.3, 1.2, 1.5], vertical_alignment="center")
        group = c1.selectbox("Income Level", fies_groups, format_func=tokens.DECILE_LONG.get, key="pp_group",
                             help="Families are ranked by income and split into ten equal groups. "
                                  "\"10–20%\" is the second-lowest group.")
        area = c2.selectbox("Area", areas, format_func=area_label, key="pp_area_sel")
        view = c3.segmented_control("Comparison View", ["Monthly", "Annual"], default="Monthly", required=True, key="pp_view")
        with c4:
            shell.filter_stat("Selected household segment", tokens.DECILE_SHORT[group],
                              "FIES 2023 income level", tone="sm")

    # Get purchasing power series for the selected area
    series = data.get_purchasing_power(area=area)
    if view == "Annual":                                    # Aggregate to annual averages
        yearly = series.assign(date=series["date"].dt.year).groupby("date", as_index=False)["value"].mean()
        yearly["date"] = yearly["date"].astype(str).add("-01-01").astype("datetime64[ns]")
        series = yearly
    first, last = series["value"].iloc[0], series["value"].iloc[-1]  # First and last values

    # Main chart (left) and FIES snapshot (right)
    main, side = st.columns([2.5, 1])
    with main:
        with st.container(key="card_pp_trend"):
            shell.panel_header("Purchasing Power Trend", f"Purchasing power of the peso, {area_label(area)}",
                               right=("Annual average" if view == "Annual" else "Monthly"))
            st.plotly_chart(trend_figure(series, "Purchasing power"), config={"displayModeBar": False})
            st.caption(f"From {month_label(series['date'].iloc[0]) if view == 'Monthly' else series['date'].iloc[0].year} to "
                       f"{month_label(series['date'].iloc[-1]) if view == 'Monthly' else series['date'].iloc[-1].year}, "
                       f"purchasing power went from ₱{first:.2f} to ₱{last:.2f} ({(last / first - 1) * 100:+.1f}%). "
                       "Purchasing power is not published by income group.")
    fies = data.get_fies_by_decile(area)                      # Get FIES data for this area
    row = fies[fies["decile"] == group].iloc[0]               # Selected decile's row
    overall = fies[fies["decile"] == "All Income Groups"].iloc[0]  # All-income row
    with side:
        st.markdown(f"**Household Snapshot**  \nFIES 2023 · {tokens.DECILE_LONG[group]}")
        shell.mini_card("Household Income", f"₱{row['income']:,.1f}k", "thousand pesos", "per family", tone="green")
        shell.mini_card("Household Expenditure", f"₱{row['expenditure']:,.1f}k", "thousand pesos", "per family", tone="gold")
        shell.mini_card("Household Savings", f"₱{row['savings']:,.1f}k", f"{row['savings_rate']:.1f}% of income", "per family", tone="green")
        groups = fies[fies["decile"] != "All Income Groups"]  # Individual deciles only
        with st.container(key="insight_pp"):
            lowest = groups.iloc[0]
            highest = groups.iloc[-1]
            if group == "All Income Groups":
                text = (f"Across all families, {row['savings_rate']:.1f}% of income is saved on average. "
                        f"The bottom 10% of earners save {lowest['savings_rate']:.1f}% and the top 10% "
                        f"{highest['savings_rate']:.1f}%.")
            else:
                who = (tokens.DECILE_SHORT[group].lower() if group in ("First Decile", "Tenth Decile")
                       else tokens.DECILE_SHORT[group] + " income group")
                text = (f"Families in the {who} keep {row['savings_rate']:.1f}% of income after "
                        f"spending (₱{row['savings']:,.1f}k of ₱{row['income']:,.1f}k), compared with "
                        f"{overall['savings_rate']:.1f}% for all families.")
            shell.insight_card("Financial Insight", [("Savings after spending", text)])

    # Grouped bar chart: income, spending, savings across all deciles
    with st.container(key="card_pp_groups"):
        shell.panel_header("Income, Spending and Savings from Lowest to Highest Earners",
                           "Average per family, " + area_label(area) + ". Families are ranked by income and split "
                           "into 10 equal groups.", right="FIES 2023")
        st.plotly_chart(group_bars(groups, group), config={"displayModeBar": False})
    st.info(tokens.FIES_NOTE, icon=":material/info:")  # Note about FIES being a 2023 snapshot


render()                                               # Execute the page when Streamlit loads it
