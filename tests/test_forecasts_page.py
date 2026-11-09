"""Tests for the Forecasting screen."""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from app import theme
from app.components import forecast_charts as charts
from backend import data

PAGE = str(Path(__file__).resolve().parents[1] / "app" / "pages" / "forecasts.py")
TIMEOUT = 120


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(PAGE, default_timeout=TIMEOUT)
    at.run()
    assert not at.exception, at.exception
    return at


def _control(at, label, kind="segmented_control"):
    widgets = getattr(at, kind) if hasattr(at, kind) else at.get(kind)
    return next(w for w in widgets if w.label == label)


def _html(at):
    return "\n".join(m.value for m in at.markdown)


def test_page_renders_with_defaults(app):
    html = _html(app)
    assert "Cost-of-Living Forecasting and Model Comparison" in html
    assert "Projected 6-Month Change" in html
    assert "Historical vs. Forecast: CPI" in html
    assert "Forecast Results" in html


@pytest.mark.parametrize("variable", list(theme.INDICATOR_NAMES))
@pytest.mark.parametrize("horizon", [3, 6, 12])
def test_every_indicator_and_horizon(app, variable, horizon):
    _control(app, "Forecast indicator", "button_group").set_value(variable)
    _control(app, "Forecast horizon", "button_group").set_value(horizon)
    app.run()
    assert not app.exception, app.exception
    assert f"Projected {horizon}-Month Change" in _html(app)


def test_forecast_page_has_no_evaluation_selectboxes(app):
    assert len(app.selectbox) == 0


def test_show_other_models(app):
    app.toggle[0].set_value(True)
    app.run()
    assert not app.exception, app.exception


def test_forecast_figure_has_history_forecast_and_band():
    forecast = data.get_forecast("cpi", 12)
    history = data.get_cpi(start="2024-01")
    fig = charts.forecast_figure(history, forecast, "cpi", "ARIMA")
    names = [t.name for t in fig.data]
    assert "Actual (PSA)" in names and "Forecast (ARIMA)" in names and "95% prediction interval" in names
    forecast_trace = next(t for t in fig.data if t.name == "Forecast (ARIMA)")
    assert pd.Timestamp(forecast_trace.x[0]) == history["date"].iloc[-1]


def test_model_comparison_colours_each_model():
    metrics = data.get_model_metrics("cpi")
    fig = charts.model_comparison_figure(metrics, "cpi", "rmse")
    bar = fig.data[0]
    selected_label = next(l for l in bar.y if l.startswith(data.get_final_model()))
    index = list(bar.y).index(selected_label)
    assert bar.marker.color[index] == theme.MODEL_COLORS[data.get_final_model()]
    assert bar.x[-1] == min(bar.x)


def test_format_value():
    assert theme.format_value("cpi", 136.4) == "136.4"
    assert theme.format_value("inflation", 6.1) == "6.1%"
    assert theme.format_value("purchasing_power", 0.73) == "₱0.73"
