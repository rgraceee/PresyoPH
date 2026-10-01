"""Screen 6: Forecasts and Model Comparison.

Built by Member 2 on top of backend/data.py; Member 3 supports the layout.
Answers the instructor's comment to forecast inflation and purchasing power
too: both are derived from the CPI forecast.
"""

import pandas as pd
import streamlit as st

from app import theme
from app.components import forecast_charts as charts
from backend import data

VARIABLES = list(theme.INDICATOR_NAMES)
HORIZONS = [3, 6, 12]
HISTORY_MONTHS = 36

# Evaluation periods offered in the model comparison, mapped to the
# (evaluation, period) values in the backend's metrics.
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
    """Everything the page needs that does not depend on the controls."""
    info = data.get_model_info()
    latest = data.get_latest()
    main_test_winner = _rule_winner(data.get_model_metrics("cpi", "main_test", EVALUATION_OPTIONS[
        "Main test: Sep 2025 – Aug 2026"][1]))
    return info, latest, main_test_winner


def _rule_winner(metrics):
    """The selection rule (lowest on at least 2 of 3 metrics, else lowest
    RMSE) among the proposal models, for explaining results in captions."""
    table = metrics[metrics["in_proposal"]].set_index("model")
    wins = pd.Series([table[m].idxmin() for m in METRIC_LABELS]).value_counts()
    return wins.index[0] if wins.iloc[0] >= 2 else table["rmse"].idxmin()


def kpi_cards(variable, horizon, forecast, latest, final_model):
    current = latest[variable]
    first, last = forecast.iloc[0], forecast.iloc[-1]
    step_error = data.get_error_by_step(variable, model=final_model)
    typical_error = step_error.loc[step_error["step"] == horizon, "mae"].iloc[0]

    cols = st.columns(4)
    cols[0].metric(
        f"Latest actual ({current['date']:%b %Y})",
        theme.format_value(variable, current["value"]),
        border=True, height="stretch",
    )
    cols[1].metric(
        f"Next month ({first['date']:%b %Y})",
        theme.format_value(variable, first["forecast"]),
        delta=theme.format_value(variable, first["forecast"] - current["value"]).replace("₱-", "-₱"),
        delta_color="off",
        help=f"95% range: {theme.format_value(variable, first['lower'])} to {theme.format_value(variable, first['upper'])}",
        border=True, height="stretch",
    )
    cols[2].metric(
        f"In {horizon} months ({last['date']:%b %Y})",
        theme.format_value(variable, last["forecast"]),
        help=f"95% range: {theme.format_value(variable, last['lower'])} to {theme.format_value(variable, last['upper'])}",
        border=True, height="stretch",
    )
    cols[3].metric(
        f"Typical error {horizon} months ahead",
        "± " + theme.format_error(variable, typical_error),
        help=(f"How far {final_model}'s forecasts were from the actual values, on average, "
              f"{horizon} months ahead, across six past test periods."),
        border=True, height="stretch",
    )


def forecast_section(variable, horizon, final_model, show_other_models):
    forecast = data.get_forecast(variable, horizon)
    first_month = forecast["date"].iloc[0]
    history_start = first_month - pd.DateOffset(months=HISTORY_MONTHS)
    history = data.get_series(variable, start=history_start)

    comparison = None
    if show_other_models:
        others = [m for m in data.get_model_metrics(variable)["model"] if m != final_model]
        comparison = {m: data.get_forecast(variable, horizon, model=m) for m in others}

    st.plotly_chart(charts.forecast_figure(history, forecast, variable, final_model, comparison),
                    config={"displayModeBar": False})

    if variable == "inflation" and (forecast["date"] >= pd.Timestamp("2027-04-01")).any():
        st.info(
            "**Why inflation drops in April 2027:** prices jumped in March–April 2026. From April 2027, "
            "prices are compared with that already-high level, so the year-on-year rate falls even though "
            "prices are still forecast to rise. This is called a *base effect*.",
            icon=":material/info:",
        )
    if variable != "cpi":
        st.caption(
            f"Only CPI is forecast by the model. The {theme.INDICATOR_NAMES[variable].lower()} forecast is "
            "calculated from the CPI forecast using PSA's formula, so the forecasts always agree with each other."
        )

    with st.expander("Forecast table"):
        table = forecast.rename(columns={"date": "Month", "forecast": "Forecast",
                                         "lower": "Lower (95%)", "upper": "Upper (95%)"})
        fmt = theme.VALUE_FORMATS[variable]
        st.dataframe(
            table.drop(columns="step"),
            hide_index=True,
            column_config={
                "Month": st.column_config.DateColumn(format="MMM YYYY"),
                "Forecast": st.column_config.NumberColumn(format=fmt),
                "Lower (95%)": st.column_config.NumberColumn(format=fmt),
                "Upper (95%)": st.column_config.NumberColumn(format=fmt),
            },
        )
        st.download_button(
            "Download forecast (CSV)",
            forecast.assign(variable=variable, model=final_model).to_csv(index=False),
            file_name=f"presyoph_{variable}_forecast_{horizon}m.csv",
            mime="text/csv",
        )


def comparison_section(variable, info, main_test_winner, show_other_models):
    final_model = info["final_model"]
    st.subheader("How accurate were the models?")
    st.markdown(
        f"Each model forecast CPI 12 months ahead from six different points in the past, and the forecasts "
        f"were compared with what actually happened. **{final_model}** was chosen because it was the most "
        f"accurate overall. {METRIC_HELP}"
    )

    left, right = st.columns([3, 2])
    period_label = left.selectbox("Evaluation period", list(EVALUATION_OPTIONS))
    metric = right.segmented_control("Error measure", list(METRIC_LABELS), default="rmse",
                                     format_func=METRIC_LABELS.get, required=True)
    evaluation, period = EVALUATION_OPTIONS[period_label]
    metrics = data.get_model_metrics(variable, evaluation, period)
    if not show_other_models:
        metrics = metrics[metrics["in_proposal"]]

    chart_col, table_col = st.columns([3, 2])
    chart_col.plotly_chart(charts.model_comparison_figure(metrics, variable, metric),
                           config={"displayModeBar": False})

    table = metrics.assign(
        Model=[m + ("" if p else " (extra)") + (" ✓ selected" if s else "")
               for m, p, s in zip(metrics["model"], metrics["in_proposal"], metrics["is_selected_model"])]
    ).sort_values(metric)
    table_col.dataframe(
        table[["Model", "mae", "rmse", "mape"]],
        hide_index=True,
        column_config={
            "mae": st.column_config.NumberColumn("MAE", format="%.3f"),
            "rmse": st.column_config.NumberColumn("RMSE", format="%.3f"),
            "mape": st.column_config.NumberColumn("MAPE", format="%.2f%%"),
        },
    )

    if variable == "inflation" and metric == "mape":
        st.warning(
            "MAPE is unreliable for inflation: when inflation is low (around 1%), even a small miss becomes a "
            "large percentage. Compare models using MAE or RMSE instead.",
            icon=":material/warning:",
        )
    if evaluation == "main_test" and period and period.startswith("full") and main_test_winner != final_model:
        st.caption(
            f"On this period alone {main_test_winner} has the lowest error, largely because of a sudden price "
            f"jump in March–April 2026. Across all six evaluation periods, {final_model} is the most accurate, "
            "which is why it was chosen."
        )

    proposal_models = list(metrics.loc[metrics["in_proposal"], "model"])
    models = list(metrics["model"]) if show_other_models else proposal_models
    test_tab, step_tab = st.tabs(["Test period: forecast vs. actual", "Error by months ahead"])
    with test_tab:
        predictions = data.get_test_predictions(variable, "main_test")
        actual = data.get_series(variable, start="2024-09")
        st.plotly_chart(charts.test_period_figure(actual, predictions, variable, models),
                        config={"displayModeBar": False})
        st.caption("Each model forecast September 2025 – August 2026 using only data up to August 2025.")
    with step_tab:
        errors = data.get_error_by_step(variable)
        st.plotly_chart(charts.error_by_step_figure(errors, variable, final_model, models),
                        config={"displayModeBar": False})
        st.caption("Forecasts become less accurate the further ahead they go. Dotted lines mark the 3-, 6-, and "
                   "12-month views.")


def method_notes(info, main_test_winner):
    final = info["final_model_params"][info["final_model"]]
    basis_note = (
        f" It was originally planned for the September 2025 – August 2026 test period alone, where "
        f"{main_test_winner} would have been chosen; the basis was widened because that period contains an "
        "unusual price jump."
        if main_test_winner != info["final_model"] else ""
    )
    with st.expander("How the forecast was made"):
        st.markdown(f"""
- **Data:** national Consumer Price Index, all items (2018 = 100), January 2018 – {pd.Timestamp(info['data']['end']):%B %Y}, from the Philippine Statistics Authority (PSA).
- **Models compared:** ARIMA, Linear Regression, and Moving Average, as in the proposal. ETS is shown as an extra comparison only.
- **Final model:** {info['final_model']}{f" {tuple(final['order'])} with an average increase of {final['drift_per_month']:.2f} index points per month" if 'order' in final else ''}.
- **How it was chosen:** {info['selection']['rule']} The rule was applied to all six evaluation periods together (72 forecast months per model).{basis_note}
- **Inflation and purchasing power** are calculated from the CPI forecast with PSA's formulas: inflation = CPI ÷ CPI a year earlier − 1; purchasing power = 1 ÷ (CPI ÷ 100).
""")


def disclaimer():
    st.divider()
    st.caption(
        "**Forecast disclaimer:** forecasts are statistical estimates based only on past CPI patterns. They do "
        "not account for events such as fuel price changes, typhoons, or policy changes, and are not financial "
        "advice. **Source:** Philippine Statistics Authority (PSA), OpenSTAT."
    )


def render():
    st.title("Forecasts and Model Comparison")
    st.caption("What prices may do over the next year, and how accurate the forecasting models have been.")

    with st.spinner("Loading data…"):
        info, latest, main_test_winner = load_page_data()
    final_model = info["final_model"]

    c1, c2, c3 = st.columns([3, 2, 2], vertical_alignment="bottom")
    variable = c1.segmented_control("Indicator", VARIABLES, default="cpi",
                                    format_func=theme.INDICATOR_SHORT_NAMES.get, required=True)
    horizon = c2.segmented_control("Forecast horizon", HORIZONS, default=12,
                                   format_func=lambda h: f"{h} months", required=True)
    show_other_models = c3.toggle("Show other models", help="Add the models that were not selected to the charts.")

    forecast = data.get_forecast(variable, horizon)
    kpi_cards(variable, horizon, forecast, latest, final_model)
    forecast_section(variable, horizon, final_model, show_other_models)
    st.divider()
    comparison_section(variable, info, main_test_winner, show_other_models)
    method_notes(info, main_test_winner)
    disclaimer()


render()
