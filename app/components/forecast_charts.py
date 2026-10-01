"""Plotly figures for the Forecasts and Model Comparison screen.

Pure functions: DataFrames in, Plotly figure out. No Streamlit calls, so
they can be tested and reused on other pages (e.g. the Home page's mini
forecast).
"""

import pandas as pd
import plotly.graph_objects as go

from app import theme

LAYOUT = dict(
    template="plotly_white",
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    hovermode="x unified",
)


def _hex_to_rgba(color, alpha):
    color = color.lstrip("#")
    r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def forecast_figure(history, forecast, variable, model, comparison=None):
    """Recent actual values, the selected model's forecast, and its 95%
    prediction interval.

    history: DataFrame with date, value (actual data before the forecast).
    forecast: DataFrame with date, forecast, lower, upper.
    comparison: optional {model name: forecast DataFrame} drawn as thin lines.
    """
    color = theme.INDICATOR_COLORS[variable]
    hover = theme.PLOTLY_HOVER_FORMATS[variable]
    fig = go.Figure()

    # Interval band: upper edge, then lower edge filled up to it.
    fig.add_trace(go.Scatter(
        x=forecast["date"], y=forecast["upper"], mode="lines", line=dict(width=0),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=forecast["date"], y=forecast["lower"], mode="lines", line=dict(width=0),
        fill="tonexty", fillcolor=_hex_to_rgba(color, 0.15), name="95% prediction interval",
        hoverinfo="skip",
    ))

    fig.add_trace(go.Scatter(
        x=history["date"], y=history["value"], mode="lines", name="Actual (PSA)",
        line=dict(color=theme.ACTUAL_COLOR, width=2),
        hovertemplate=f"%{{y:{hover}}}<extra>Actual</extra>",
    ))

    # Join the forecast to the last actual point so the line is continuous.
    last = history.iloc[[-1]].rename(columns={"value": "forecast"})
    joined = pd.concat([last[["date", "forecast"]], forecast[["date", "forecast"]]])
    fig.add_trace(go.Scatter(
        x=joined["date"], y=joined["forecast"], mode="lines+markers", name=f"Forecast ({model})",
        line=dict(color=color, width=2.5, dash="dash"), marker=dict(size=5),
        hovertemplate=f"%{{y:{hover}}}<extra>Forecast</extra>",
    ))

    for name, other in (comparison or {}).items():
        fig.add_trace(go.Scatter(
            x=other["date"], y=other["forecast"], mode="lines", name=name,
            line=dict(color=theme.MODEL_COLORS.get(name, theme.MUTED_COLOR), width=1.2),
            opacity=0.8, hovertemplate=f"%{{y:{hover}}}<extra>{name}</extra>",
        ))

    fig.add_vline(x=history["date"].iloc[-1], line=dict(color=theme.MUTED_COLOR, dash="dot", width=1))
    fig.update_layout(**LAYOUT, height=420, yaxis_title=theme.INDICATOR_UNITS[variable])
    return fig


def model_comparison_figure(metrics, variable, metric="rmse"):
    """Horizontal bars of one error metric per model, lowest at the top.

    metrics: DataFrame from backend get_model_metrics() for one variable.
    The selected model is drawn in its colour; others are muted.
    """
    table = metrics.sort_values(metric, ascending=False)
    labels = [m + ("  (extra)" if not p else "") for m, p in zip(table["model"], table["in_proposal"])]
    colors = [theme.INDICATOR_COLORS[variable] if s else theme.MUTED_COLOR for s in table["is_selected_model"]]
    if metric == "mape":
        text = [f"{v:.2f}%" for v in table[metric]]
    else:
        text = [theme.format_error(variable, v) for v in table[metric]]

    fig = go.Figure(go.Bar(
        x=table[metric], y=labels, orientation="h", marker_color=colors, text=text,
        textposition="outside", cliponaxis=False, hoverinfo="skip",
    ))
    fig.update_layout(**{**LAYOUT, "hovermode": False}, height=260, showlegend=False,
                      xaxis_title=f"{metric.upper()} (lower is better)")
    return fig


def test_period_figure(actual, predictions, variable, models):
    """Actual values against each model's forecasts over an evaluation period.

    actual: DataFrame with date, value covering the period and some history.
    predictions: DataFrame from backend get_test_predictions() (one origin).
    """
    hover = theme.PLOTLY_HOVER_FORMATS[variable]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=actual["date"], y=actual["value"], mode="lines+markers", name="Actual (PSA)",
        line=dict(color=theme.ACTUAL_COLOR, width=2), marker=dict(size=4),
        hovertemplate=f"%{{y:{hover}}}<extra>Actual</extra>",
    ))
    for model in models:
        rows = predictions[predictions["model"] == model]
        fig.add_trace(go.Scatter(
            x=rows["date"], y=rows["forecast"], mode="lines", name=model,
            line=dict(color=theme.MODEL_COLORS.get(model, theme.MUTED_COLOR), width=2),
            hovertemplate=f"%{{y:{hover}}}<extra>{model}</extra>",
        ))
    start = predictions["date"].min()
    fig.add_vline(x=start - pd.Timedelta(days=15), line=dict(color=theme.MUTED_COLOR, dash="dot", width=1))
    fig.update_layout(**LAYOUT, height=380, yaxis_title=theme.INDICATOR_UNITS[variable])
    return fig


def error_by_step_figure(errors, variable, selected_model, models, highlight_steps=(3, 6, 12)):
    """Mean absolute error at each step ahead, one line per model."""
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
    for step in highlight_steps:
        fig.add_vline(x=step, line=dict(color=theme.MUTED_COLOR, dash="dot", width=1))
    fig.update_layout(**LAYOUT, height=340, xaxis=dict(title="Months ahead", dtick=1),
                      yaxis_title=f"Average error ({theme.INDICATOR_UNITS[variable].split(',')[0]})")
    return fig
