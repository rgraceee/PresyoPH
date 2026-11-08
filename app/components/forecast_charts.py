"""
================================================================================
FILE: app/components/forecast_charts.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
This file builds Plotly chart figures for the Forecasts page and Model
Comparison screen. All functions are pure: they take DataFrames as input and
return Plotly Figure objects. They do NOT call Streamlit directly, so they
can be tested independently.

Functions:
  - forecast_figure(): historical vs. forecast with 95% interval
  - model_comparison_figure(): horizontal bars of error metrics per model
  - test_period_figure(): actual vs. forecast over an evaluation period
  - error_by_step_figure(): MAE at each step ahead, one line per model

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- app/pages/forecasts.py: Does NOT import from here directly (uses app.ui.charts instead).
- tests/test_forecasts_page.py: Imports from app.components.forecast_charts and
  tests forecast_figure(), model_comparison_figure().
- app/theme.py: Provides MODEL_COLORS, ACTUAL_COLOR, MUTED_COLOR,
  PLOTLY_HOVER_FORMATS, INDICATOR_UNITS, format_error().
- app/ui/charts.py: Has a similar forecast_figure() but uses tokens colours
  instead of theme colours.

NOTE: app/ui/charts.py also has a forecast_figure() function. This file's
version is used by tests; app/ui/charts.py's version is used by pages.
Both produce similar output but with different colour sources.
"""

"""Plotly figures for the Forecasts and Model Comparison screen.

Pure functions: DataFrames in, Plotly figure out. No Streamlit calls, so
they can be tested and reused on other pages (e.g. the Home page's mini
forecast).
"""

import pandas as pd                                   # pandas: DataFrame operations
import plotly.graph_objects as go                     # plotly: chart library

from app import theme                                 # theme: colours, formats, indicator units

# Default layout for all charts in this file.
LAYOUT = dict(
    template="plotly_white",                         # Clean white theme
    margin=dict(l=10, r=10, t=40, b=10),             # Small margins
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),  # Legend at top-left
    hovermode="x unified",                           # One hover box for all traces at same x
)


def _hex_to_rgba(color, alpha):
    """Convert a hex colour to RGBA string with given alpha.
    
    Parameters
    ----------
    color : str
        Hex colour like "#1B5E4B".
    alpha : float
        Opacity from 0 to 1.
    
    Returns
    -------
    str
        RGBA string like "rgba(27,94,75,0.15)".
    """
    color = color.lstrip("#")                          # Remove #
    r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))  # Parse RGB from hex
    return f"rgba({r},{g},{b},{alpha})"               # Return RGBA format


def forecast_figure(history, forecast, variable, model, comparison=None):
    """Build a forecast chart: actual values, forecast line, and 95% interval.
    
    Shows:
      - Actual (PSA) historical data as a solid line
      - Forecast as a dashed line starting from the last actual point
      - 95% prediction interval as a shaded band
      - Optional comparison models as thin lines
      - A vertical line at the split between history and forecast
    
    Parameters
    ----------
    history : pandas.DataFrame
        Columns: date, value (actual data before the forecast).
    forecast : pandas.DataFrame
        Columns: date, forecast, lower, upper.
    variable : str
        One of "cpi", "inflation", "purchasing_power" (for hover format and y-axis title).
    model : str
        Model name (for colour and legend label).
    comparison : dict or None
        Optional {model_name: forecast_dataframe} drawn as thin lines.
    
    Returns
    -------
    plotly.graph_objects.Figure
    """
    color = theme.MODEL_COLORS.get(model, theme.MUTED_COLOR)  # Colour for this model
    hover = theme.PLOTLY_HOVER_FORMATS[variable]             # Hover number format
    fig = go.Figure()

    # Trace 1: Upper bound of prediction interval (invisible, used as fill boundary)
    fig.add_trace(go.Scatter(
        x=forecast["date"], y=forecast["upper"], mode="lines", line=dict(width=0),
        showlegend=False, hoverinfo="skip",
    ))
    # Trace 2: Lower bound filled up to upper, creating shaded band
    fig.add_trace(go.Scatter(
        x=forecast["date"], y=forecast["lower"], mode="lines", line=dict(width=0),
        fill="tonexty", fillcolor=_hex_to_rgba(color, 0.15), name="95% prediction interval",
        hoverinfo="skip",
    ))
    # Trace 3: Actual historical data
    fig.add_trace(go.Scatter(
        x=history["date"], y=history["value"], mode="lines", name="Actual (PSA)",
        line=dict(color=theme.ACTUAL_COLOR, width=2),
        hovertemplate=f"%{{y:{hover}}}<extra>Actual</extra>",
    ))
    # Join last actual point to first forecast point for continuous line
    last = history.iloc[[-1]].rename(columns={"value": "forecast"})
    joined = pd.concat([last[["date", "forecast"]], forecast[["date", "forecast"]]])
    # Trace 4: Forecast line (dashed, with markers)
    fig.add_trace(go.Scatter(
        x=joined["date"], y=joined["forecast"], mode="lines+markers", name=f"Forecast ({model})",
        line=dict(color=color, width=2.5, dash="dash"), marker=dict(size=5),
        hovertemplate=f"%{{y:{hover}}}<extra>Forecast</extra>",
    ))
    # Trace 5+: Optional comparison models (thin, semi-transparent)
    for name, other in (comparison or {}).items():
        fig.add_trace(go.Scatter(
            x=other["date"], y=other["forecast"], mode="lines", name=name,
            line=dict(color=theme.MODEL_COLORS.get(name, theme.MUTED_COLOR), width=1.2),
            opacity=0.8, hovertemplate=f"%{{y:{hover}}}<extra>{name}</extra>",
        ))
    # Vertical line at the split point
    fig.add_vline(x=history["date"].iloc[-1], line=dict(color=theme.MUTED_COLOR, dash="dot", width=1))
    fig.update_layout(**LAYOUT, height=420, yaxis_title=theme.INDICATOR_UNITS[variable])
    return fig


def model_comparison_figure(metrics, variable, metric="rmse"):
    """Build horizontal bars of one error metric per model, lowest at the top.
    
    Parameters
    ----------
    metrics : pandas.DataFrame
        Output of backend.data.get_model_metrics() for one variable.
    variable : str
        One of "cpi", "inflation", "purchasing_power".
    metric : str
        One of "mae", "rmse", "mape".
    
    Returns
    -------
    plotly.graph_objects.Figure
    """
    table = metrics.sort_values(metric, ascending=False)  # Sort so lowest error is at top
    labels = [m + ("  (extra)" if not p else "") for m, p in zip(table["model"], table["in_proposal"])]
    # Mark non-proposal models (ETS) with "(extra)"
    colors = [
        theme.MODEL_COLORS.get(model, theme.MUTED_COLOR)
        for model in table["model"]
    ]
    if metric == "mape":
        text = [f"{v:.2f}%" for v in table[metric]]       # MAPE shown as percentage
    else:
        text = [theme.format_error(variable, v) for v in table[metric]]  # Use theme formatter

    fig = go.Figure(go.Bar(
        x=table[metric], y=labels, orientation="h", marker_color=colors, text=text,
        textposition="outside", cliponaxis=False, hoverinfo="skip",
    ))
    fig.update_layout(**{**LAYOUT, "hovermode": False}, height=260, showlegend=False,
                      xaxis_title=f"{metric.upper()} (lower is better)")
    return fig


def test_period_figure(actual, predictions, variable, models):
    """Build a chart of actual values vs. each model's forecasts over an evaluation period.
    
    Parameters
    ----------
    actual : pandas.DataFrame
        Columns: date, value (actual PSA data covering the period plus some history).
    predictions : pandas.DataFrame
        Output of backend.data.get_test_predictions() (one origin).
    variable : str
        One of "cpi", "inflation", "purchasing_power".
    models : list of str
        Model names to show.
    
    Returns
    -------
    plotly.graph_objects.Figure
    """
    hover = theme.PLOTLY_HOVER_FORMATS[variable]
    fig = go.Figure()
    # Actual data trace
    fig.add_trace(go.Scatter(
        x=actual["date"], y=actual["value"], mode="lines+markers", name="Actual (PSA)",
        line=dict(color=theme.ACTUAL_COLOR, width=2), marker=dict(size=4),
        hovertemplate=f"%{{y:{hover}}}<extra>Actual</extra>",
    ))
    # One trace per model's forecast
    for model in models:
        rows = predictions[predictions["model"] == model]
        fig.add_trace(go.Scatter(
            x=rows["date"], y=rows["forecast"], mode="lines", name=model,
            line=dict(color=theme.MODEL_COLORS.get(model, theme.MUTED_COLOR), width=2),
            hovertemplate=f"%{{y:{hover}}}<extra>{model}</extra>",
        ))
    # Vertical line marking the start of the evaluation period
    start = predictions["date"].min()
    fig.add_vline(x=start - pd.Timedelta(days=15), line=dict(color=theme.MUTED_COLOR, dash="dot", width=1))
    fig.update_layout(**LAYOUT, height=380, yaxis_title=theme.INDICATOR_UNITS[variable])
    return fig


def error_by_step_figure(errors, variable, selected_model, models, highlight_steps=(3, 6, 12)):
    """Build a line chart of mean absolute error at each step ahead (1-12 months).
    
    One line per model. The selected model is highlighted with a thicker line.
    
    Parameters
    ----------
    errors : pandas.DataFrame
        Output of backend.data.get_error_by_step().
    variable : str
        One of "cpi", "inflation", "purchasing_power".
    selected_model : str
        The selected model name (highlighted).
    models : list of str
        Model names to show.
    highlight_steps : tuple of int
        Steps to mark with vertical lines (default 3, 6, 12).
    
    Returns
    -------
    plotly.graph_objects.Figure
    """
    fig = go.Figure()
    for model in models:
        rows = errors[errors["model"] == model]
        selected = model == selected_model
        fig.add_trace(go.Scatter(
            x=rows["step"], y=rows["mae"], mode="lines+markers", name=model,
            line=dict(color=theme.MODEL_COLORS.get(model, theme.MUTED_COLOR), width=3 if selected else 1.5),
            marker=dict(size=7 if selected else 4),
            hovertemplate="%{y:.2f}<extra>" + model + "</extra>",
        ))
    # Vertical lines at 3, 6, 12 months for reference
    for step in highlight_steps:
        fig.add_vline(x=step, line=dict(color=theme.MUTED_COLOR, dash="dot", width=1))
    fig.update_layout(**LAYOUT, height=340, xaxis=dict(title="Months ahead", dtick=1),
                      yaxis_title=f"Average error ({theme.INDICATOR_UNITS[variable].split(',')[0]})")
    return fig
