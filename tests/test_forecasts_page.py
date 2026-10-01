"""Tests for the Forecasts and Model Comparison screen (app/pages/forecasts.py).

Uses Streamlit's AppTest to run the real page without a browser, then
switches every control and checks that the page renders without errors.
"""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app import theme
from app.components import forecast_charts as charts
from backend import data

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")
TIMEOUT = 120  # the first run reads the raw Excel files


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    at.run()
    assert not at.exception, at.exception
    return at


def _control(at, label, kind="segmented_control"):
    widgets = getattr(at, kind) if hasattr(at, kind) else at.get(kind)
    return next(w for w in widgets if w.label == label)


def test_page_renders_with_defaults(app):
    assert app.title[0].value == "Forecasts and Model Comparison"
    labels = [m.label for m in app.metric]
    assert labels[0].startswith("Latest actual")
    assert len(app.metric) == 4


@pytest.mark.parametrize("variable", list(theme.INDICATOR_NAMES))
@pytest.mark.parametrize("horizon", [3, 6, 12])
def test_every_indicator_and_horizon(app, variable, horizon):
    _control(app, "Indicator", "button_group").set_value(variable)
    _control(app, "Forecast horizon", "button_group").set_value(horizon)
    app.run()
    assert not app.exception, app.exception
    assert app.metric[2].label.startswith(f"In {horizon} months")


def test_every_evaluation_period_and_metric(app):
    period = app.selectbox[0]
    for option in period.options:
        for metric in ["rmse", "mae", "mape"]:
            period.set_value(option)
            _control(app, "Error measure", "button_group").set_value(metric)
            app.run()
            assert not app.exception, (option, metric, app.exception)


def test_show_other_models(app):
    app.toggle[0].set_value(True)
    app.run()
    assert not app.exception, app.exception


# --- Chart builders --------------------------------------------------------------

def test_forecast_figure_has_history_forecast_and_band():
    forecast = data.get_forecast("cpi", 12)
    history = data.get_cpi(start="2024-01")
    fig = charts.forecast_figure(history, forecast, "cpi", "ARIMA")
    names = [t.name for t in fig.data]
    assert "Actual (PSA)" in names and "Forecast (ARIMA)" in names and "95% prediction interval" in names
    # The forecast line starts at the last actual point so the line is continuous.
    forecast_trace = next(t for t in fig.data if t.name == "Forecast (ARIMA)")
    assert pd.Timestamp(forecast_trace.x[0]) == history["date"].iloc[-1]


def test_model_comparison_highlights_selected_model():
    metrics = data.get_model_metrics("cpi")
    fig = charts.model_comparison_figure(metrics, "cpi", "rmse")
    bar = fig.data[0]
    selected_label = next(l for l in bar.y if l.startswith(data.get_final_model()))
    index = list(bar.y).index(selected_label)
    assert bar.marker.color[index] == theme.INDICATOR_COLORS["cpi"]
    # Lowest error is drawn at the top (last bar in a horizontal chart).
    assert bar.x[-1] == min(bar.x)


def test_format_value():
    assert theme.format_value("cpi", 136.4) == "136.4"
    assert theme.format_value("inflation", 6.1) == "6.1%"
    assert theme.format_value("purchasing_power", 0.73) == "₱0.73"
