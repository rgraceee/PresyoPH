"""Screen 1: Dashboard. The at-a-glance page (Figma: Dashboard)."""

import pandas as pd
import streamlit as st

from app import theme
from app.ui import charts, queries, shell, tokens
from app.ui.layout import month_label
from backend import data

TREND_GROUPS = ["Food and non-alcoholic beverages", "Housing, water, electricity, gas and other fuels",
                "Transport", "Health"]
PERIODS = {"6 months": 6, "12 months": 12, "24 months": 24, "All": None}


def summary_cards(latest, fies_all):
    cpi, infl, power = latest["cpi"], latest["inflation"], latest["purchasing_power"]
    cols = st.columns(4)
    with cols[0]:
        shell.kpi_card("Cost of Living Index", theme.format_value("cpi", cpi["value"]), "CPI", tone="green",
                       delta=f"{'▲' if cpi['change'] >= 0 else '▼'} {abs(cpi['change']):.1f} pts", bad=cpi["change"] > 0,
                       help="Consumer Price Index, 2018 = 100. A CPI of 136 means prices are about 36% above 2018.",
                       foot=f"vs. {month_label(cpi['date'] - pd.DateOffset(months=1))}")
    with cols[1]:
        shell.kpi_card("Peso Purchasing Power", theme.format_value("purchasing_power", power["value"]), "₱",
                       delta=f"{'▲' if power['change'] >= 0 else '▼'} {abs(power['change']):.2f}", bad=power["change"] < 0,
                       tone="gold", help=f"Today's peso buys what about {power['value'] * 100:.0f} centavos bought in 2018.",
                       foot="vs. last month")
    with cols[2]:
        shell.kpi_card("Average Household Spending", f"₱{fies_all['expenditure']:,.1f}k", "₱", tone="sage",
                       help="From the 2023 Family Income and Expenditure Survey (thousand pesos per family). "
                            "A 2023 snapshot, not a monthly figure.",
                       foot="FIES 2023 snapshot")
    with cols[3]:
        shell.kpi_card("Inflation Rate", theme.format_value("inflation", infl["value"]), "%", tone="deep",
                       delta=f"{'▲' if infl['change'] >= 0 else '▼'} {abs(infl['change']):.1f} pts", bad=infl["change"] > 0,
                       help="How much higher prices are than in the same month a year earlier.", foot="vs. last month")


def price_trend_card(labels):
    with st.container(key="card_trend"):
        head, pick = st.columns([3.2, 1], vertical_alignment="top")
        with head:
            shell.panel_header("Price Trend (Selected Categories)", "Consumer Price Index by household necessity")
        period = pick.selectbox("Period", list(PERIODS), index=1, key="home_period", label_visibility="collapsed")
        chosen = st.multiselect("Categories", labels, default=[g for g in TREND_GROUPS if g in labels], key="home_groups",
                                label_visibility="collapsed", placeholder="Choose categories")
        if not chosen:
            st.info("Choose at least one category to see its price trend.")
            return
        items = data.list_categories().set_index("label")["item"]
        _, end = data.get_date_range("cpi")
        start = None if PERIODS[period] is None else end - pd.DateOffset(months=PERIODS[period] - 1)
        frame = pd.DataFrame({g: data.get_series("cpi", start, None, item=items[g]).set_index("date")["value"] for g in chosen})
        st.plotly_chart(charts.time_series_figure(frame, y_title="CPI (2018 = 100)", hover=".1f", height=300),
                        config={"displayModeBar": False})


def savings_card():
    with st.container(key="card_savings"):
        shell.panel_header("Savings by Household Income Group",
                           "Share of income saved, FIES 2023 (lowest to highest income)", icon="house")
        groups = data.get_fies_by_decile().query("decile != 'All Income Groups'")
        labels = [tokens.DECILE_SHORT[d].split(" ")[0] for d in groups["decile"]]
        st.plotly_chart(charts.banded_column_figure(labels, groups["savings_rate"], suffix="%", height=300),
                        config={"displayModeBar": False})


def regional_card():
    with st.container(key="card_regions"):
        shell.panel_header("Cost of Living by Region", f"Consumer Price Index, {month_label(data.get_date_range('cpi')[1])}", icon="pin")
        ranking = data.get_regional_comparison("cpi")
        colors = [shell.rank_color(i, len(ranking), higher_is_better=False) for i in range(len(ranking))]
        fig = charts.ranked_bar_figure(ranking["region"].str.replace(r"\s*\(.*\)", "", regex=True), ranking["value"],
                                       reference=ranking.attrs["national"], hover=".1f", height=420)
        fig.update_traces(marker_color=colors)
        st.plotly_chart(fig, config={"displayModeBar": False})
        shell.rank_legend(higher_is_better=False)


def top_increases_card():
    with st.container(key="card_top"):
        shell.panel_header("Top 5 Price Increases (1 Month)", "Household necessities with the biggest CPI rise", icon="wallet")
        changes = queries.get_category_changes(1)
        rows = [{"rank": r["rank"], "name": r["label"], "sub": f"CPI {r['value']:.1f}", "change": r["change_pct"]}
                for _, r in changes.head(5).iterrows()]
        shell.ranked_list(rows)
        st.caption(f"{month_label(changes.attrs['start'])} to {month_label(changes.attrs['end'])}.")


def insights_card(latest, top, ranking):
    power = latest["purchasing_power"]
    hi, lo = ranking.iloc[0], ranking.iloc[-1]
    changes = queries.get_category_changes(1)
    top_month = changes.iloc[0]
    items = [
        ("Rising prices in " + top["label"],
         f"Year-on-year inflation is {top['inflation']:.1f}%, against {top['all_items_inflation']:.1f}% for all items. "
         f"This month {top_month['label']} rose most ({top_month['change_pct']:+.1f}%)."),
        ("Purchasing power " + ("declined" if power["change"] < 0 else "held or improved"),
         f"The peso's purchasing power is {power['value']:.2f}, {power['change']:+.2f} from last month."),
        ("Regional differences",
         f"CPI is highest in {hi['region']} ({hi['value']:.1f}) and lowest in {lo['region']} ({lo['value']:.1f})."),
    ]
    with st.container(key="insight_home"):
        shell.insight_card("Key Insights", items)
        st.page_link("pages/reports.py", label="View detailed report", icon=":material/arrow_forward:")
        st.caption("Generated automatically from the latest PSA data.")


def forecast_card(latest):
    with st.container(key="card_forecast"):
        shell.panel_header("Forecast (Next 3 Months)", "CPI forecast from the selected model, with 95% range")
        left, right = st.columns([2.6, 1])
        forecast = data.get_forecast("cpi", 3)
        history = data.get_series("cpi", start=forecast["date"].iloc[0] - pd.DateOffset(months=12))
        info = data.get_model_info()
        left.plotly_chart(charts.forecast_figure(history, forecast, "cpi", info["final_model"]),
                          config={"displayModeBar": False})
        pp = data.get_forecast("purchasing_power", 3).iloc[-1]
        now = latest["purchasing_power"]["value"]
        with right:
            shell.mini_card(f"Projected Purchasing Power ({month_label(pp['date'])})", f"{pp['forecast']:.2f}",
                            f"{'▲' if pp['forecast'] >= now else '▼'} {abs(pp['forecast'] / now - 1) * 100:.1f}%",
                            f"vs. {month_label(latest['purchasing_power']['date'])}", tone="green")
            st.page_link("pages/forecasts.py", label="Full forecasts", icon=":material/trending_up:")


def render():
    shell.page_header(shell.greeting(),
                      "Here's the latest cost of living and purchasing power insights for Filipino households.")
    latest = data.get_latest()
    fies_all = data.get_fies_by_decile().query("decile == 'All Income Groups'").iloc[0]
    top = data.get_top_category()
    ranking = data.get_regional_comparison("cpi")

    summary_cards(latest, fies_all)
    labels = list(data.list_categories()["label"])
    main, side = st.columns([2.3, 1])
    with main:
        price_trend_card(labels)
        region_col, top5_col = st.columns(2)
        with region_col:
            regional_card()
        with top5_col:
            top_increases_card()
        forecast_card(latest)
    with side:
        savings_card()
        insights_card(latest, top, ranking)
    quote_col, _ = st.columns([2, 3])
    with quote_col:
        shell.quote_card()


render()
