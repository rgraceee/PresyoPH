"""Screen 4: Purchasing Power and Household Finances (Figma: Purchasing Power and Household Financial Analysis).

Purchasing power is a monthly series (national and regional). FIES is a 2023
snapshot by income group; the two are shown together but are not the same data.
"""

import plotly.graph_objects as go
import streamlit as st

from app.ui import charts, shell, tokens
from app.ui.charts import LAYOUT
from app.ui.layout import area_label, area_options, month_label
from backend import data

MEASURES = {"income": "Income", "expenditure": "Spending", "savings": "Savings"}


def trend_figure(series, label):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series["date"], y=series["value"], mode="lines+markers", name=label, fill="tozeroy",
                             line=dict(color=tokens.INDICATOR_COLORS["inflation"], width=3), marker=dict(size=5),
                             fillcolor="rgba(233,170,43,0.10)", hovertemplate="%{y:.2f}<extra>" + label + "</extra>"))
    fig.add_hline(y=1.0, line_dash="dot", line_color="#9CA3AF", annotation_text="2018 purchasing power (₱1.00)",
                  annotation_position="top right")
    fig.update_layout(**LAYOUT, height=330, showlegend=False,
                      yaxis=dict(title="Purchasing power (2018 = ₱1.00)", range=[max(0, series["value"].min() * 0.85), 1.1],
                                 gridcolor="#e8e8de"))
    return fig


def group_bars(groups, selected):
    labels = [tokens.DECILE_SHORT[d] for d in groups["decile"]]
    fig = charts.grouped_bar_figure(labels, {MEASURES[m]: groups[m] for m in MEASURES},
                                    {MEASURES[m]: tokens.FIES_COLORS[m] for m in MEASURES}, y_title="Thousand pesos per family",
                                    height=360)
    if selected in set(groups["decile"]):
        fig.add_vrect(x0=list(groups["decile"]).index(selected) - 0.5, x1=list(groups["decile"]).index(selected) + 0.5,
                      fillcolor="rgba(27,94,75,0.08)", line_width=0)
    return fig


def render():
    shell.page_header("Purchasing Power and Household Financial Analysis",
                      "Understand how household income, spending, and savings relate to the peso's purchasing power.",
                      shell.pill("Financial data based on the 2023 FIES snapshot", tone="gold"))

    areas = [data.NATIONAL] + data.list_areas("region")
    fies_groups = [d for d in tokens.DECILE_SHORT]
    with st.container(key="filter_pp"):
        c1, c2, c3, c4 = st.columns([1.4, 1.3, 1.2, 1.5], vertical_alignment="center")
        group = c1.selectbox("Income Group", fies_groups, format_func=lambda d: "All income groups" if d == "All Income Groups"
                             else tokens.DECILE_SHORT[d] + " decile", key="pp_group")
        area = c2.selectbox("Area", areas, format_func=area_label, key="pp_area_sel")
        view = c3.segmented_control("Comparison View", ["Monthly", "Annual"], default="Monthly", required=True, key="pp_view")
        with c4:
            shell.filter_stat("Selected household segment", "All incomes" if group == "All Income Groups" else tokens.DECILE_SHORT[group],
                              "FIES 2023 income group", tone="sm")

    series = data.get_purchasing_power(area=area)
    if view == "Annual":
        yearly = series.assign(date=series["date"].dt.year).groupby("date", as_index=False)["value"].mean()
        yearly["date"] = yearly["date"].astype(str).add("-01-01").astype("datetime64[ns]")
        series = yearly
    first, last = series["value"].iloc[0], series["value"].iloc[-1]

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
    fies = data.get_fies_by_decile(area)
    row = fies[fies["decile"] == group].iloc[0]
    overall = fies[fies["decile"] == "All Income Groups"].iloc[0]
    with side:
        st.markdown(f"**Household Snapshot**  \nFIES 2023 · {'All income groups' if group == 'All Income Groups' else tokens.DECILE_SHORT[group] + ' decile'}")
        shell.mini_card("Household Income", f"₱{row['income']:,.1f}k", "thousand pesos", "per family", tone="green")
        shell.mini_card("Household Expenditure", f"₱{row['expenditure']:,.1f}k", "thousand pesos", "per family", tone="gold")
        shell.mini_card("Household Savings", f"₱{row['savings']:,.1f}k", f"{row['savings_rate']:.1f}% of income", "per family", tone="green")

    main, side = st.columns([2.5, 1])
    with main:
        with st.container(key="card_pp_groups"):
            shell.panel_header("Income, Expenditure and Savings by Income Group",
                               "Average household financial position across income groups, " + area_label(area), right="FIES 2023")
            groups = fies[fies["decile"] != "All Income Groups"]
            st.plotly_chart(group_bars(groups, group), config={"displayModeBar": False})
    with side:
        with st.container(key="insight_pp"):
            lowest = groups.iloc[0]
            highest = groups.iloc[-1]
            if group == "All Income Groups":
                text = (f"Across all income groups, families save {row['savings_rate']:.1f}% of their income on average. "
                        f"The lowest-income tenth saves {lowest['savings_rate']:.1f}% and the highest-income tenth "
                        f"{highest['savings_rate']:.1f}%.")
            else:
                text = (f"The {tokens.DECILE_SHORT[group]} income group keeps {row['savings_rate']:.1f}% of income after "
                        f"spending (₱{row['savings']:,.1f}k of ₱{row['income']:,.1f}k), compared with "
                        f"{overall['savings_rate']:.1f}% for all families.")
            shell.insight_card("Financial Insight", [("Savings after spending", text)])
    st.info(tokens.FIES_NOTE, icon=":material/info:")


render()
