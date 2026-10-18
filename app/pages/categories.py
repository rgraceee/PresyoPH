"""Screen 3: Household Necessities (Figma: Household Necessities Category Analysis)."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.ui import queries, shell, tokens
from app.ui.charts import LAYOUT
from app.ui.layout import month_label
from backend import data

PERIODS = {"6 months": 6, "12 months": 12, "24 months": 24, "All (since 2018)": None}
BAR_COLORS = ["#1B5E4B", "#E9AA2B", "#EE7B30", "#D94B3D", "#6FA06B", "#8FA79A"]


def category_trend_figure(series, average, name):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series["date"], y=series["value"], mode="lines+markers", name=name, fill="tozeroy",
                             line=dict(color=tokens.INDICATOR_COLORS["cpi"], width=3), fillcolor="rgba(27,94,75,0.07)",
                             hovertemplate="%{y:.1f}<extra>" + name + "</extra>"))
    fig.add_trace(go.Scatter(x=average["date"], y=average["value"], mode="lines", name="All categories average",
                             line=dict(color="#9CA3AF", width=2, dash="dash"), hovertemplate="%{y:.1f}<extra>All items</extra>"))
    low = min(series["value"].min(), average["value"].min())
    fig.update_layout(**LAYOUT, height=380, yaxis=dict(title="Price index (2018 = 100)", range=[low * 0.92, series["value"].max() * 1.06],
                                                         gridcolor="#e8e8de"))
    return fig


def comparison_bars(ranking, selected_label):
    values = ranking["value"]
    scale = values.max()
    rows = []
    for i, r in ranking.reset_index(drop=True).iterrows():
        color = BAR_COLORS[min(i, len(BAR_COLORS) - 1)]
        bold = "font-weight:800" if r["label"] == selected_label else ""
        rows.append(f'<tr><td style="font-size:11.5px;width:42%;{bold}">{shell.esc(r["label"])}</td>'
                    f'<td><div class="pp-bar"><i style="width:{r["value"] / scale * 100:.1f}%;background:{color}"></i></div></td>'
                    f'<td class="num" style="font-weight:700;width:48px">{r["value"]:.1f}</td></tr>')
    st.markdown(f'<table class="pp-tbl">{"".join(rows)}</table>', unsafe_allow_html=True)


def render():
    shell.page_header("Household Necessities Category Analysis",
                      "Compare price movements across the essential categories that shape Filipino household expenses.",
                      shell.chip("Updated " + month_label(data.get_date_range("cpi")[1])))

    categories = data.list_categories()
    labels = list(categories["label"])
    items = categories.set_index("label")["item"]
    if st.session_state.get("cat_select") not in labels:
        st.session_state["cat_select"] = labels[0]

    with st.container(key="filter_cats"):
        c1, c2, c3 = st.columns([1.5, 1.2, 1.5], vertical_alignment="center")
        label = c1.selectbox("Necessity Category", labels, key="cat_select")
        period = c2.selectbox("Period", list(PERIODS), key="cat_period")
        first, last = data.get_date_range("cpi")
        start = first if PERIODS[period] is None else last - pd.DateOffset(months=PERIODS[period] - 1)
        series = data.get_series("cpi", start, None, item=items[label])
        average = data.get_series("cpi", start, None)
        change = (series["value"].iloc[-1] / series["value"].iloc[0] - 1) * 100
        with c3:
            shell.filter_stat("Current Category Index", f"{series['value'].iloc[-1]:.1f}",
                              f"{'▲' if change >= 0 else '▼'} {abs(change):.1f}% vs. start of period", tone="dn" if change > 0 else "up")

    main, side = st.columns([1.5, 1])
    with main:
        with st.container(key="card_cat_trend"):
            shell.panel_header("Category Price Trend", f"Price index movement for {label.lower()}", right=period)
            st.plotly_chart(category_trend_figure(series, average, label), config={"displayModeBar": False})
    with side:
        show_all = st.toggle("Show all 13 categories", key="cat_all",
                             help="The Figma design lists six; PSA publishes thirteen commodity groups.")
        ranking = data.get_category_comparison("cpi")
        if not show_all:
            top = ranking.head(6)
            ranking_view = top if label in set(top["label"]) else ranking[ranking["label"].isin(set(top["label"]) | {label})]
        else:
            ranking_view = ranking
        with st.container(key="card_cat_compare"):
            shell.panel_header("Category Comparison", f"Current index, {month_label(ranking.attrs['date'])}", right="Price index")
            comparison_bars(ranking_view, label)
        changes = queries.get_category_changes(max(1, len(series) - 1))
        with st.container(key="card_cat_rank"):
            shell.panel_header("Fastest-Rising Categories", "Ranked by change in the selected period", right="Change")
            shell.ranked_list([{"rank": r["rank"], "name": r["label"], "sub": "Household necessity", "change": r["change_pct"]}
                               for _, r in (changes if show_all else changes.head(6)).iterrows()])
    st.caption("Categories are PSA's 13 commodity groups. Item-level prices (such as rice or cooking oil) are not part of "
               "the datasets used by PresyoPH.")


render()
