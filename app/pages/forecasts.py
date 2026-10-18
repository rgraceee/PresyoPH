"""Forecasting screen in the Figma layout: projected values, results table and
model comparison. Everything comes from backend.data (the ARIMA pipeline's
outputs); nothing is computed here except display changes.

The full evaluation (error measures by period, forecast vs. actual, error by
months ahead) stays on the existing Forecasts page, linked at the bottom.
"""

import pandas as pd
import streamlit as st

from app import theme
from app.ui import charts, shell, tokens
from app.components import forecast_charts as eval_charts
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
    """Inflation is already a percentage, so its change is in points; the others are % of the base."""
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
    """One row per forecast month with its 95% range and change from the previous period."""
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


def model_table_card(variable):
    """MAE, RMSE, MAPE per model from the pooled evaluation that the selection rule used."""
    metrics = data.get_model_metrics(variable)
    metrics = metrics[metrics["in_proposal"]].sort_values("rmse")
    best_rmse = metrics["rmse"].min()
    rows = []
    for r in metrics.itertuples():
        best = r.is_selected_model
        chip = '<span class="pp-badge-best">BEST MODEL</span>' if best else ""
        color = tokens.RANK_COLORS[0] if best else "#E9AA2B"
        rows.append(
            f'<tr class="{"sel" if best else ""}"><td><b>{shell.esc(r.model)}</b>{chip}'
            f'<small>{shell.esc(MODEL_BLURBS.get(r.model, ""))}</small></td>'
            f'<td class="num">{r.mae:.3f}</td><td class="num">{r.rmse:.3f}</td><td class="num">{r.mape:.2f}%</td>'
            f'<td style="width:32%"><div class="pp-bar"><i style="width:{best_rmse / r.rmse * 100:.0f}%;background:{color}"></i></div></td></tr>')
    shell.panel_header("Forecast Model Comparison",
                       f"Accuracy for {theme.INDICATOR_SHORT_NAMES[variable]} across all six evaluation periods", right="Lower error is better")
    st.markdown('<table class="pp-tbl"><tr><th>Forecast model</th><th class="num">MAE</th><th class="num">RMSE</th>'
                f'<th class="num">MAPE</th><th>Performance (relative RMSE)</th></tr>{"".join(rows)}</table>', unsafe_allow_html=True)
    if variable == "inflation":
        st.caption("MAPE is unreliable for inflation when the rate is low; rely on MAE and RMSE.")


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
        with st.container(key="card_fc_models"):
            model_table_card(variable)
    with right:
        with st.container(key="card_fc_results"):
            results_card(variable, horizon, forecast, latest, final_model)
        with st.container(key="insight_fc"):
            shell.insight_card("Forecast Disclaimer", [("Estimates only", tokens.FORECAST_DISCLAIMER)], icon="info")

    st.divider()
    with st.container(key="full_model_evaluation"):
        shell.page_header("Full Model Evaluation", "Review accuracy by evaluation period, compare forecasts with actual values, and inspect errors by forecast horizon.")
        comparison_section(variable, info, main_test_winner, show_other)
        method_notes(info, main_test_winner)
        disclaimer()


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
    chart_col.plotly_chart(eval_charts.model_comparison_figure(metrics, variable, metric),
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
        st.plotly_chart(eval_charts.test_period_figure(actual, predictions, variable, models),
                        config={"displayModeBar": False})
        st.caption("Each model forecast September 2025 – August 2026 using only data up to August 2025.")
    with step_tab:
        errors = data.get_error_by_step(variable)
        st.plotly_chart(eval_charts.error_by_step_figure(errors, variable, final_model, models),
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



main()
