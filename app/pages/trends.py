"""
================================================================================
FILE: app/pages/trends.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
Screen 2: Cost-of-Living Trends. Shows historical CPI and inflation rate on a
dual-axis chart. Users can filter by area (national/region), start date, and
end date. Also shows period summary statistics (highest, lowest, average, 
percent change).

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- app/streamlit_app.py: Registers this page as "trends".
- backend/data.py: Calls data.get_series(), data.get_period_stats(), data.get_date_range(),
  data.NATIONAL.
- app/ui/shell.py: Calls shell.page_header(), shell.filter_title(), shell.filter_stat(),
  shell.mini_card(), shell.insight_card(), shell.chip().
- app/ui/layout.py: Calls area_label(), area_options(), month_label(), month_options().
- app/ui/charts.py: Does NOT directly import charts here; uses LAYOUT from charts.
- app/ui/theme.py: Does NOT import theme here (uses app.ui.tokens instead).
- app/ui/tokens.py: Calls tokens.INDICATOR_COLORS.

================================================================================
"""

"""Screen 2: Cost-of-Living Trends (Figma: Cost-of-Living Trend Analysis)."""

import plotly.graph_objects as go                     # plotly: chart library
import streamlit as st                                # streamlit: UI components

from app.ui import shell, tokens                      # shell: UI components; tokens: indicator colours
from app.ui.charts import LAYOUT                      # LAYOUT: default Plotly layout settings
from app.ui.layout import area_label, area_options, month_label, month_options  # UI helpers
from backend import data                              # backend: data access functions


def dual_axis_figure(cpi, inflation, height=420):
    """Build a chart with CPI on the left axis and inflation rate on the right axis.
    
    Parameters
    ----------
    cpi : pandas.DataFrame
        Columns: date, value (CPI values).
    inflation : pandas.DataFrame
        Columns: date, value (inflation values).
    height : int
        Chart height in pixels.
    
    Returns
    -------
    plotly.graph_objects.Figure
    """
    fig = go.Figure()                                  # Create empty figure
    # CPI trace: filled area chart on left y-axis
    fig.add_trace(go.Scatter(
        x=cpi["date"], y=cpi["value"], name="Consumer Price Index", mode="lines", fill="tozeroy",
        line=dict(color=tokens.INDICATOR_COLORS["cpi"], width=3), fillcolor="rgba(27,94,75,0.08)",
        hovertemplate="%{y:.1f}<extra>CPI</extra>",
    ))
    # Inflation trace: line chart on right y-axis (only if data exists)
    if not inflation.empty:
        fig.add_trace(go.Scatter(
            x=inflation["date"], y=inflation["value"], name="Inflation rate", mode="lines", yaxis="y2",
            line=dict(color=tokens.INDICATOR_COLORS["inflation"], width=3),
            hovertemplate="%{y:.1f}%<extra>Inflation</extra>",
        ))
    low = cpi["value"].min()                           # Lowest CPI value for y-axis range
    fig.update_layout(
        **LAYOUT, height=height,
        yaxis=dict(title="CPI value", range=[max(0, low * 0.9), cpi["value"].max() * 1.05], showgrid=True, gridcolor="#e8e8de"),
        yaxis2=dict(title="Inflation rate", overlaying="y", side="right", ticksuffix="%", showgrid=False, rangemode="tozero"),
    )
    return fig


def render():
    """Render the Cost-of-Living Trends page."""
    # Page header with data freshness chip
    shell.page_header("Cost-of-Living Trend Analysis",
                      "Track historical price movements and inflation patterns across the Philippines.",
                      shell.chip("Data updated through " + month_label(data.get_date_range("cpi")[1])))

    # Get all available months for the date pickers
    months = month_options("cpi")
    with st.container(key="filter_trends"):              # Filter controls container
        c0, c1, c2, c3 = st.columns([1.2, 1.6, 1.1, 1.1], vertical_alignment="center")
        with c0:
            shell.filter_title("Analysis Filters", "Refine the trend data shown below")
        # Area selector: national, area group, or region
        area = c1.selectbox("Region", area_options(), format_func=area_label, key="trend_area")
        # Start date selector
        start = c2.selectbox("Start Date", months, index=0, format_func=month_label, key="trend_start")
        # End date selector: only months on or after start (prevents reversed ranges)
        end_months = [m for m in months if m >= start]
        end = c3.selectbox("End Date", end_months, index=len(end_months) - 1, format_func=month_label, key="trend_end")

    # Fetch data for the selected area and date range
    cpi = data.get_series("cpi", start, end, area)
    inflation = data.get_series("inflation", start, end, area)

    # Main chart (left, wider) and summary stats (right, narrower)
    main, side = st.columns([2.6, 1])
    with main:
        with st.container(key="card_trend_main"):
            shell.panel_header("CPI and Inflation Trend", "Consumer Price Index with the monthly inflation rate comparison",
                               right=f"{month_label(start)} to {month_label(end)}")
            st.plotly_chart(dual_axis_figure(cpi, inflation), config={"displayModeBar": False})
            st.caption("Inflation is available from January 2019. All values are published PSA data; none are projected "
                       "here (see Forecasting for projections).")
    with side:
        st.markdown("**Period Summary**  \n" + area_label(area))  # Show selected area name
        stats = data.get_period_stats("cpi", start, end, area)    # Get summary statistics
        shell.mini_card("Highest Value", f"{stats['highest']['value']:.1f}", month_label(stats["highest"]["date"]),
                        "CPI index", tone="gold")
        shell.mini_card("Lowest Value", f"{stats['lowest']['value']:.1f}", month_label(stats["lowest"]["date"]),
                        "CPI index", tone="green")
        shell.mini_card("Average Value", f"{stats['average']:.1f}", f"{stats['months']} months", "Selected period", tone="green")
        with st.container(key="insight_trend"):
            shell.insight_card("Trend Insight", [(
                "Change over the selected period",
                f"CPI changed by {stats['percent_change']:+.1f}% from {month_label(stats['start'])} to {month_label(stats['end'])}, "
                "showing how prices have moved for households.")])
        # Additional inflation stats if data exists
        if not inflation.empty:
            istats = data.get_period_stats("inflation", start, end, area)
            st.caption(f"Inflation in this period: highest {istats['highest']['value']:.1f}% ({month_label(istats['highest']['date'])}), "
                       f"lowest {istats['lowest']['value']:.1f}% ({month_label(istats['lowest']['date'])}), "
                       f"average {istats['average']:.1f}%.")


render()                                               # Execute the page when Streamlit loads it
