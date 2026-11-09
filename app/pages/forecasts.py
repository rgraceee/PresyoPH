"""Forecasting screen: projected values, results table and model comparison."""

import pandas as pd
import streamlit as st

from app import theme
from app.ui import charts, shell
from backend import data

VARIABLES = list(theme.INDICATOR_NAMES)
HORIZONS = [3, 6, 12]
HISTORY_MONTHS = 36
MODEL_BLURBS = {
    "ARIMA": "Auto-regressive integrated moving average",
    "Linear Regression": "Trend-based statistical regression",
    "Moving Average": "Baseline built from recent observations",
    "ETS": "Exponential smoothing (extra comparison only)",
}

EVALUATION_OPTIONS = {
    "All six evaluation periods (used to choose the model)": ("pooled", None),
    "Main test: Sep 2025 – Aug 2026": ("main_test", "full test (Sep 2025 - Aug 2026)"),
    "Main test, before the price shock (Sep 2025 – Feb 2026)": ("main_test", "before shock (Sep 2025 - Feb 2026)"),
    "Main test, after the price shock (Mar – Aug 2026)": ("main_test", "after shock (Mar 2026 - Aug 2026)"),
    "Average of the five earlier periods": ("rolling_average", None),
}
METRIC_LABELS = {
    "rmse": "RMSE",
    "mae": "MAE",
    "mape": "MAPE",
}
METRIC_HELP = (
    "**MAE** is the average size of the error. **RMSE** is similar but penalises large misses more. "
    "**MAPE** is the average error as a percentage of the actual value. Lower is better for all three."
)


@st.cache_data(show_spinner=False)
def load_page_data():
    info = data.get_model_info()
    latest = data.get_latest()
    main_test_winner = _rule_winner(data.get_model_metrics("cpi", "main_test", EVALUATION_OPTIONS[
        "Main test: Sep 2025 – Aug 2026"][1]))
    return info, latest, main_test_winner


def _rule_winner(metrics):
    table = metrics[metrics["in_proposal"]].set_index("model")
    wins = pd.Series([table[m].idxmin() for m in METRIC_LABELS]).value_counts()
    return wins.index[0] if wins.iloc[0] >= 2 else table["rmse"].idxmin()


def _change_text(variable, diff, base):
    if variable == "inflation":
        return f"{abs(diff):.1f} pts"
    return f"{abs(diff / base * 100):.1f}%"


def chart_card(variable, horizon, forecast, final_model, show_other):
    history = data.get_series(variable, start=forecast["date"].iloc[0] - pd.DateOffset(months=HISTORY_MONTHS))
    comparison = None
    if show_other:
        others = [m for m in data.get_model_metrics(variable)["model"] if m != final_model]
        comparison = {m: data.get_forecast(variable, horizon, model=m) for m in others}
    shell.panel_header(f"Historical vs. Forecast: {theme.INDICATOR_SHORT_NAMES[variable]}",
                       f"Historical observations with a {horizon}-month projected outlook", right=f"{final_model} model",
                       icon="trend")
    st.plotly_chart(charts.forecast_figure(history, forecast, variable, final_model, comparison),
                    config={"displayModeBar": False})
    if variable == "inflation" and (forecast["date"] >= pd.Timestamp("2027-04-01")).any():
        st.info("**Why inflation drops in April 2027:** prices jumped in March–April 2026. From April 2027, prices are "
                "compared with that already-high level, so the year-on-year rate falls even though prices are still "
                "forecast to rise (a *base effect*).", icon=":material/info:")
    if variable != "cpi":
        st.caption(f"Only CPI is forecast by the model. The {theme.INDICATOR_NAMES[variable].lower()} forecast is "
                   "calculated from the CPI forecast using PSA's formula, so the forecasts always agree with each other.")


def results_card(variable, horizon, forecast, latest, final_model):
    previous = latest[variable]["value"]
    rows = []
    for i, r in enumerate(forecast.itertuples()):
        diff = r.forecast - previous
        worse = diff < 0 if variable == "purchasing_power" else diff > 0
        rows.append(
            f'<tr><td>{r.date:%b %Y}<small>{"Next period" if i == 0 else f"Month {i + 1}"}</small></td>'
            f'<td class="num">{theme.format_value(variable, r.forecast)}</td>'
            f'<td class="num">{theme.format_value(variable, r.lower)} to {theme.format_value(variable, r.upper)}</td>'
            f'<td class="num {"dn" if worse else "up"}">{"▲" if diff >= 0 else "▼"} {_change_text(variable, diff, previous)}</td></tr>')
        previous = r.forecast
    shell.panel_header("Forecast Results", "Point estimates and 95% prediction range", right=f"{len(forecast)} periods", icon="file")
    st.markdown('<table class="pp-tbl"><tr><th>Period</th><th class="num">Forecast</th><th class="num">Range</th>'
                f'<th class="num">Change</th></tr>{"".join(rows)}</table>', unsafe_allow_html=True)
    st.download_button("Download forecast (CSV)", forecast.assign(variable=variable, model=final_model).to_csv(index=False),
                       file_name=f"presyoph_{variable}_forecast_{horizon}m.csv", mime="text/csv", key="fc_download")


def main():
    with st.spinner("Loading data…"):
        info, latest, main_test_winner = load_page_data()
    final_model = info["final_model"]
    shell.page_header("Cost-of-Living Forecasting and Model Comparison",
                      "Explore projected movements and compare forecasting model performance.",
                      shell.chip(f"{pd.Timestamp(info['generated_at']):%B} {pd.Timestamp(info['generated_at']).day}, "
                                 f"{pd.Timestamp(info['generated_at']).year}", icon="calendar", boxed=True, sub="Forecast generated"))

    with st.container(key="filter_fc"):
        c1, c2, c3, c4 = st.columns([2.2, 2.2, 1.3, 1.6], vertical_alignment="center")
        variable = c1.segmented_control("Forecast indicator", VARIABLES, default="cpi",
                                        format_func=theme.INDICATOR_SHORT_NAMES.get, required=True)
        horizon = c2.segmented_control("Forecast horizon", HORIZONS, default=6,
                                       format_func=lambda h: f"{h} months", required=True)
        show_other = c3.toggle("Show other models", help="Add the models that were not selected to the chart.")
        forecast = data.get_forecast(variable, horizon)
        diff = forecast["forecast"].iloc[-1] - latest[variable]["value"]
        worse = diff < 0 if variable == "purchasing_power" else diff > 0
        with c4:
            shell.filter_stat(f"Projected {horizon}-Month Change", f"{'▲' if diff >= 0 else '▼'} {_change_text(variable, diff, latest[variable]['value'])}",
                              f"{theme.INDICATOR_SHORT_NAMES[variable]} forecast, {final_model}", tone="dn" if worse else "up")

    left, right = st.columns([2.1, 1])
    with left:
        with st.container(key="card_fc_chart"):
            chart_card(variable, horizon, forecast, final_model, show_other)
    with right:
        with st.container(key="card_fc_results"):
            results_card(variable, horizon, forecast, latest, final_model)


main()
