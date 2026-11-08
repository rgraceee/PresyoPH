"""
================================================================================
FILE: app/pages/forecasts.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
Forecasting screen showing projected CPI, inflation, and purchasing power
values. Users can select an indicator, forecast horizon (3/6/12 months), and
optionally compare other models. Shows:

  - Historical vs. forecast chart with 95% prediction interval
  - Table of forecast months with ranges and changes
  - Download button for forecast CSV

The page also links to a full model evaluation page (not part of this file).

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- app/streamlit_app.py: Registers this page as "forecasting".
- backend/data.py: Calls data.get_model_info(), data.get_latest(), data.get_model_metrics(),
  data.get_forecast(), data.get_series(), data.get_final_model().
- app/ui/shell.py: Calls shell.page_header(), shell.chip(), shell.panel_header(),
  shell.filter_stat().
- app/ui/charts.py: Calls charts.forecast_figure().
- app/ui/theme.py: Calls theme.INDICATOR_NAMES, theme.INDICATOR_SHORT_NAMES,
  theme.format_value(), theme.MODEL_COLORS.
- app/components/forecast_charts.py: Not directly imported here.
- tests/test_forecasts_page.py: Tests this page with AppTest.

================================================================================
"""

"""Forecasting screen in the Figma layout: projected values, results table and
model comparison. Everything comes from backend.data (the ARIMA pipeline's
outputs); nothing is computed here except display changes.

The full evaluation (error measures by period, forecast vs. actual, error by
months ahead) stays on the existing Forecasts page, linked at the bottom.
"""

import pandas as pd                                   # pandas: DataFrame operations
import streamlit as st                                # streamlit: UI components

from app import theme                                 # theme: indicator names, formats, colours
from app.ui import charts, shell                      # shell: UI components; charts: Plotly figures
from backend import data                              # backend: data access functions

VARIABLES = list(theme.INDICATOR_NAMES)               # ["cpi", "inflation", "purchasing_power"]
HORIZONS = [3, 6, 12]                                 # Available forecast horizons
HISTORY_MONTHS = 36                                   # Months of history to show on chart
# Plain-language descriptions of each model for the UI.
MODEL_BLURBS = {
    "ARIMA": "Auto-regressive integrated moving average",
    "Linear Regression": "Trend-based statistical regression",
    "Moving Average": "Baseline built from recent observations",
    "ETS": "Exponential smoothing (extra comparison only)",
}

# Evaluation periods for the model comparison, mapped to (evaluation, period)
# values used by backend.data.get_model_metrics().
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


@st.cache_data(show_spinner=False)                    # Cache results so page loads faster on rerun
def load_page_data():
    """Load data needed for the page: model info, latest values, main test winner.
    
    Returns
    -------
    tuple of (dict, dict, str)
        (model_info, latest_values, main_test_winner_model_name)
    """
    info = data.get_model_info()                        # Selected model and metadata
    latest = data.get_latest()                          # Latest values for all indicators
    # Determine which model won on the main test period (for display)
    main_test_winner = _rule_winner(data.get_model_metrics("cpi", "main_test", EVALUATION_OPTIONS[
        "Main test: Sep 2025 – Aug 2026"][1]))
    return info, latest, main_test_winner


def _rule_winner(metrics):
    """Pick the winning model using the 2-of-3-metrics rule on proposal models only.
    
    Parameters
    ----------
    metrics : pandas.DataFrame
        Model metrics for one variable and period.
    
    Returns
    -------
    str
        Name of the winning model.
    """
    table = metrics[metrics["in_proposal"]].set_index("model")  # Only proposal models (ARIMA, Linear Regression, Moving Average)
    wins = pd.Series([table[m].idxmin() for m in METRIC_LABELS]).value_counts()  # Count wins per model across MAE, RMSE, MAPE
    return wins.index[0] if wins.iloc[0] >= 2 else table["rmse"].idxmin()  # 2-of-3 rule, else lowest RMSE


def _change_text(variable, diff, base):
    """Format the change from the previous period as points or percent.
    
    Inflation is already a percentage, so its change is in points; the others
    are expressed as percent of the base value.
    
    Parameters
    ----------
    variable : str
        One of "cpi", "inflation", "purchasing_power".
    diff : float
        Difference from previous period.
    base : float
        Base value for percent calculation.
    
    Returns
    -------
    str
        Formatted change text.
    """
    if variable == "inflation":
        return f"{abs(diff):.1f} pts"                    # Inflation change in percentage points
    return f"{abs(diff / base * 100):.1f}%"              # Others as percent of base


def chart_card(variable, horizon, forecast, final_model, show_other):
    """Show the historical-vs-forecast chart for one variable and horizon.
    
    Parameters
    ----------
    variable : str
        One of "cpi", "inflation", "purchasing_power".
    horizon : int
        Forecast horizon in months (3, 6, or 12).
    forecast : pandas.DataFrame
        Forecast output from data.get_forecast().
    final_model : str
        Name of the selected model.
    show_other : bool
        Whether to add other models' forecasts as comparison lines.
    """
    # Get 36 months of history before the forecast starts
    history = data.get_series(variable, start=forecast["date"].iloc[0] - pd.DateOffset(months=HISTORY_MONTHS))
    comparison = None
    if show_other:
        # Get other models' forecasts for comparison
        others = [m for m in data.get_model_metrics(variable)["model"] if m != final_model]
        comparison = {m: data.get_forecast(variable, horizon, model=m) for m in others}
    shell.panel_header(f"Historical vs. Forecast: {theme.INDICATOR_SHORT_NAMES[variable]}",
                       f"Historical observations with a {horizon}-month projected outlook", right=f"{final_model} model",
                       icon="trend")
    st.plotly_chart(charts.forecast_figure(history, forecast, variable, final_model, comparison),
                    config={"displayModeBar": False})
    # Special note: inflation drops in April 2027 due to base effect (prices were high in March-April 2026)
    if variable == "inflation" and (forecast["date"] >= pd.Timestamp("2027-04-01")).any():
        st.info("**Why inflation drops in April 2027:** prices jumped in March–April 2026. From April 2027, prices are "
                "compared with that already-high level, so the year-on-year rate falls even though prices are still "
                "forecast to rise (a *base effect*).", icon=":material/info:")
    # Note that only CPI is directly forecast; others are derived
    if variable != "cpi":
        st.caption(f"Only CPI is forecast by the model. The {theme.INDICATOR_NAMES[variable].lower()} forecast is "
                   "calculated from the CPI forecast using PSA's formula, so the forecasts always agree with each other.")


def results_card(variable, horizon, forecast, latest, final_model):
    """Show a table of forecast months with 95% range and change from previous.
    
    Parameters
    ----------
    variable : str
        One of "cpi", "inflation", "purchasing_power".
    horizon : int
        Forecast horizon in months.
    forecast : pandas.DataFrame
        Forecast output from data.get_forecast().
    latest : dict
        Output of data.get_latest().
    final_model : str
        Name of the selected model.
    """
    previous = latest[variable]["value"]                 # Current value (before forecast starts)
    rows = []
    for i, r in enumerate(forecast.itertuples()):        # One row per forecast month
        diff = r.forecast - previous
        # For purchasing power, lower is worse; for others, higher is worse
        worse = diff < 0 if variable == "purchasing_power" else diff > 0
        rows.append(
            f'<tr><td>{r.date:%b %Y}<small>{"Next period" if i == 0 else f"Month {i + 1}"}</small></td>'
            f'<td class="num">{theme.format_value(variable, r.forecast)}</td>'
            f'<td class="num">{theme.format_value(variable, r.lower)} to {theme.format_value(variable, r.upper)}</td>'
            f'<td class="num {"dn" if worse else "up"}">{"▲" if diff >= 0 else "▼"} {_change_text(variable, diff, previous)}</td></tr>')
        previous = r.forecast                            # Update previous for next iteration
    shell.panel_header("Forecast Results", "Point estimates and 95% prediction range", right=f"{len(forecast)} periods", icon="file")
    st.markdown('<table class="pp-tbl"><tr><th>Period</th><th class="num">Forecast</th><th class="num">Range</th>'
                f'<th class="num">Change</th></tr>{"".join(rows)}</table>', unsafe_allow_html=True)
    # Download button for the forecast as CSV
    st.download_button("Download forecast (CSV)", forecast.assign(variable=variable, model=final_model).to_csv(index=False),
                       file_name=f"presyoph_{variable}_forecast_{horizon}m.csv", mime="text/csv", key="fc_download")


def main():
    """Render the Forecasting page."""
    with st.spinner("Loading data…"):                    # Show spinner while loading
        info, latest, main_test_winner = load_page_data()
    final_model = info["final_model"]                    # The selected model name
    shell.page_header("Cost-of-Living Forecasting and Model Comparison",
                      "Explore projected movements and compare forecasting model performance.",
                      shell.chip(f"{pd.Timestamp(info['generated_at']):%B} {pd.Timestamp(info['generated_at']).day}, "
                                 f"{pd.Timestamp(info['generated_at']).year}", icon="calendar", boxed=True, sub="Forecast generated"))

    # Filter controls: variable, horizon, show other models
    with st.container(key="filter_fc"):
        c1, c2, c3, c4 = st.columns([2.2, 2.2, 1.3, 1.6], vertical_alignment="center")
        variable = c1.segmented_control("Forecast indicator", VARIABLES, default="cpi",
                                        format_func=theme.INDICATOR_SHORT_NAMES.get, required=True)
        horizon = c2.segmented_control("Forecast horizon", HORIZONS, default=6,
                                       format_func=lambda h: f"{h} months", required=True)
        show_other = c3.toggle("Show other models", help="Add the models that were not selected to the chart.")
        forecast = data.get_forecast(variable, horizon)   # Get forecast data
        diff = forecast["forecast"].iloc[-1] - latest[variable]["value"]  # Change from current to end of forecast
        worse = diff < 0 if variable == "purchasing_power" else diff > 0
        with c4:
            shell.filter_stat(f"Projected {horizon}-Month Change", f"{'▲' if diff >= 0 else '▼'} {_change_text(variable, diff, latest[variable]['value'])}",
                              f"{theme.INDICATOR_SHORT_NAMES[variable]} forecast, {final_model}", tone="dn" if worse else "up")

    # Two-column layout: chart (left) and results table (right)
    left, right = st.columns([2.1, 1])
    with left:
        with st.container(key="card_fc_chart"):
            chart_card(variable, horizon, forecast, final_model, show_other)
    with right:
        with st.container(key="card_fc_results"):
            results_card(variable, horizon, forecast, latest, final_model)


main()                                                  # Execute the page when Streamlit loads it
