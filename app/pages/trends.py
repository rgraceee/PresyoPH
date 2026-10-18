"""Screen 2: Cost-of-Living Trends (Figma: Cost-of-Living Trend Analysis)."""

import plotly.graph_objects as go
import streamlit as st

from app.ui import shell, tokens
from app.ui.charts import LAYOUT
from app.ui.layout import area_label, area_options, month_label, month_options
from backend import data


def dual_axis_figure(cpi, inflation, height=420):
    """CPI (left axis, area) and inflation rate (right axis, line) on one chart."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cpi["date"], y=cpi["value"], name="Consumer Price Index", mode="lines", fill="tozeroy",
        line=dict(color=tokens.INDICATOR_COLORS["cpi"], width=3), fillcolor="rgba(27,94,75,0.08)",
        hovertemplate="%{y:.1f}<extra>CPI</extra>",
    ))
    if not inflation.empty:
        fig.add_trace(go.Scatter(
            x=inflation["date"], y=inflation["value"], name="Inflation rate", mode="lines", yaxis="y2",
            line=dict(color=tokens.INDICATOR_COLORS["inflation"], width=3),
            hovertemplate="%{y:.1f}%<extra>Inflation</extra>",
        ))
    low = cpi["value"].min()
    fig.update_layout(
        **LAYOUT, height=height,
        yaxis=dict(title="CPI value", range=[max(0, low * 0.9), cpi["value"].max() * 1.05], showgrid=True, gridcolor="#e8e8de"),
        yaxis2=dict(title="Inflation rate", overlaying="y", side="right", ticksuffix="%", showgrid=False, rangemode="tozero"),
    )
    return fig


def render():
    shell.page_header("Cost-of-Living Trend Analysis",
                      "Track historical price movements and inflation patterns across the Philippines.",
                      shell.chip("Data updated through " + month_label(data.get_date_range("cpi")[1])))

    months = month_options("cpi")
    with st.container(key="filter_trends"):
        c0, c1, c2 = st.columns([1.2, 2.2, 1.6], vertical_alignment="center")
        with c0:
            shell.filter_title("Analysis Filters", "Refine the trend data shown below")
        start, end = c1.select_slider("Date Period", options=months, value=(months[0], months[-1]),
                                      format_func=month_label, key="trend_range")
        area = c2.selectbox("Region", area_options(), format_func=area_label, key="trend_area")

    cpi = data.get_series("cpi", start, end, area)
    inflation = data.get_series("inflation", start, end, area)
    main, side = st.columns([2.6, 1])
    with main:
        with st.container(key="card_trend_main"):
            shell.panel_header("CPI and Inflation Trend", "Consumer Price Index with the monthly inflation rate comparison",
                               right=f"{month_label(start)} to {month_label(end)}")
            st.plotly_chart(dual_axis_figure(cpi, inflation), config={"displayModeBar": False})
            st.caption("Inflation is available from January 2019. All values are published PSA data; none are projected "
                       "here (see Forecasting for projections).")
    with side:
        st.markdown("**Period Summary**  \n" + area_label(area))
        stats = data.get_period_stats("cpi", start, end, area)
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
        if not inflation.empty:
            istats = data.get_period_stats("inflation", start, end, area)
            st.caption(f"Inflation in this period: highest {istats['highest']['value']:.1f}% ({month_label(istats['highest']['date'])}), "
                       f"lowest {istats['lowest']['value']:.1f}% ({month_label(istats['lowest']['date'])}), "
                       f"average {istats['average']:.1f}%.")


render()
