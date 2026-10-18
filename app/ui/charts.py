"""Plotly figures for the Figma-styled screens. Colours come from app.ui.tokens,
so the Forecasts page's own chart palette (app/theme.py) is not affected."""

import math

import pandas as pd
import plotly.graph_objects as go

from app import theme
from app.ui import tokens

LAYOUT = dict(
    template="plotly_white",
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)),
    hovermode="x unified",
    xaxis=dict(showgrid=False, linecolor="#d9ddd3", tickfont=dict(size=11)),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Nunito Sans, sans-serif", color="#0F3D36", size=12),
)


def _rgba(color, alpha):
    color = color.lstrip("#")
    r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def forecast_figure(history, forecast, variable, model, comparison=None, height=420):
    """Recent actual values, the selected model's forecast and its 95% interval
    (same content as app.components.forecast_charts.forecast_figure, Figma colours)."""
    color = tokens.MODEL_COLORS.get(model, theme.MUTED_COLOR)
    hover = theme.PLOTLY_HOVER_FORMATS[variable]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=forecast["date"], y=forecast["upper"], mode="lines", line=dict(width=0),
                             showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=forecast["date"], y=forecast["lower"], mode="lines", line=dict(width=0),
                             fill="tonexty", fillcolor=_rgba(color, 0.18), name="95% prediction interval",
                             hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=history["date"], y=history["value"], mode="lines", name="Actual (PSA)",
                             line=dict(color=tokens.ACTUAL_COLOR, width=2),
                             hovertemplate=f"%{{y:{hover}}}<extra>Actual</extra>"))
    last = history.iloc[[-1]].rename(columns={"value": "forecast"})
    joined = pd.concat([last[["date", "forecast"]], forecast[["date", "forecast"]]])
    fig.add_trace(go.Scatter(x=joined["date"], y=joined["forecast"], mode="lines+markers", name=f"Forecast ({model})",
                             line=dict(color=color, width=2.5, dash="dash"), marker=dict(size=5),
                             hovertemplate=f"%{{y:{hover}}}<extra>Forecast</extra>"))
    for name, other in (comparison or {}).items():
        fig.add_trace(go.Scatter(x=other["date"], y=other["forecast"], mode="lines", name=name,
                                 line=dict(color=tokens.MODEL_COLORS.get(name, theme.MUTED_COLOR), width=1.2),
                                 opacity=0.8, hovertemplate=f"%{{y:{hover}}}<extra>{name}</extra>"))
    # Figma: the forecast period is a tinted band, with HISTORICAL / FORECAST labels at the split
    split = history["date"].iloc[-1]
    fig.add_vrect(x0=split, x1=forecast["date"].iloc[-1], fillcolor="rgba(247,185,39,0.10)", line_width=0, layer="below")
    fig.add_vline(x=split, line=dict(color=theme.MUTED_COLOR, dash="dot", width=1))
    for text, anchor, x in (("HISTORICAL", "right", split), ("FORECAST", "left", split)):
        fig.add_annotation(x=x, y=1.0, yref="paper", text=text, showarrow=False, xanchor=anchor, yanchor="top",
                           font=dict(size=10, color="#7a8a84"), xshift=-6 if anchor == "right" else 6)
    fig.update_layout(**LAYOUT, height=height, yaxis_title=theme.INDICATOR_UNITS[variable])
    fig.update_yaxes(gridcolor="#e8e8de", zeroline=False)
    return fig


def time_series_figure(frame, colors=None, y_title=None, hover=".2f", height=360, y_suffix=""):
    """Lines over time. `frame` is wide: indexed by date, one column per line."""
    fig = go.Figure()
    for i, column in enumerate(frame.columns):
        color = (colors or {}).get(column, tokens.LINE_PALETTE[i % len(tokens.LINE_PALETTE)])
        fig.add_trace(go.Scatter(
            x=frame.index, y=frame[column], mode="lines+markers" if len(frame) <= 30 else "lines", name=str(column),
            line=dict(color=color, width=2.5), marker=dict(size=6),
            hovertemplate=f"%{{y:{hover}}}{y_suffix}<extra>{column}</extra>",
        ))
    fig.update_layout(**LAYOUT, height=height, showlegend=len(frame.columns) > 1)
    fig.update_yaxes(title=y_title, ticksuffix=y_suffix, gridcolor="#e8e8de", zeroline=False)
    fig.update_xaxes(title=None)
    return fig


def ranked_bar_figure(labels, values, reference=None, reference_label="Philippines",
                      color="#2563EB", highlight=None, hover=".1f", suffix="", height=None):
    """Horizontal bars, highest at the top. `labels` and `values` must already
    be ranked. `highlight` is one label drawn in the highlight colour;
    `reference` draws a vertical line (e.g. the national value)."""
    colors = [tokens.HIGHLIGHT_COLOR if label == highlight else color for label in labels]
    fig = go.Figure(go.Bar(
        x=list(values), y=list(labels), orientation="h", marker_color=colors,
        hovertemplate=f"%{{y}}<br>%{{x:{hover}}}{suffix}<extra></extra>",
    ))
    if reference is not None:
        fig.add_vline(x=reference, line_dash="dot", line_color=tokens.ACTUAL_COLOR,
                      annotation_text=f"{reference_label}: {reference:{hover}}{suffix}",
                      annotation_position="top")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=LAYOUT["font"],
        template="plotly_white", margin=dict(l=10, r=10, t=40, b=10), showlegend=False,
        height=height or max(300, 30 * len(labels) + 80),
    )
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(ticksuffix=suffix, title=None)
    return fig


def grouped_bar_figure(categories, series, colors, y_title=None, hover=".1f", height=380):
    """Grouped vertical bars. `series` is {name: list of values}."""
    fig = go.Figure()
    for name, values in series.items():
        fig.add_trace(go.Bar(
            x=list(categories), y=list(values), name=name, marker_color=colors.get(name),
            hovertemplate=f"%{{y:{hover}}}<extra>{name}</extra>",
        ))
    fig.update_layout(**{**LAYOUT, "hovermode": "x unified"}, barmode="group", height=height)
    fig.update_yaxes(title=y_title)
    return fig


def column_figure(categories, values, color, y_title=None, suffix="", hover=".1f", height=320):
    fig = go.Figure(go.Bar(
        x=list(categories), y=list(values), marker_color=color,
        hovertemplate=f"%{{x}}<br>%{{y:{hover}}}{suffix}<extra></extra>",
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=LAYOUT["font"],
                      template="plotly_white", margin=dict(l=10, r=10, t=30, b=10), showlegend=False, height=height)
    fig.update_yaxes(title=y_title, ticksuffix=suffix)
    return fig

# Figma column-chart colours, best to worst: dark green, green, gold, orange.
BAND_COLORS = ["#145845", "#6f9f68", "#f0b82f", "#f2742d"]


def banded_column_figure(categories, values, suffix="%", hover=".1f", height=300, higher_is_better=True):
    """Rounded columns with the value above each bar, coloured in four bands by rank (Figma column chart).
    `categories` keep the order given; only the colours depend on the values."""
    values = [float(v) for v in values]
    n = len(values)
    best_first = sorted(range(n), key=lambda i: values[i], reverse=higher_is_better)
    colors = [""] * n
    for rank, i in enumerate(best_first):
        colors[i] = BAND_COLORS[min(len(BAND_COLORS) - 1, rank * len(BAND_COLORS) // n)]
    top = max(10, math.ceil((max(values) + 4) / 10) * 10)

    fig = go.Figure(go.Bar(
        x=list(categories), y=values, marker_color=colors,
        text=[f"{v:.0f}{suffix}" for v in values], textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color="#0d3e3b"),
        hovertemplate=f"%{{x}}<br>%{{y:{hover}}}{suffix}<extra></extra>",
    ))
    try:
        fig.update_traces(marker_cornerradius=6)  # rounded tops (Plotly 5.24+)
    except ValueError:
        pass
    fig.update_layout(
        template="plotly_white", height=height, bargap=0.3, showlegend=False,
        margin=dict(l=36, r=6, t=22, b=30), font=LAYOUT["font"],
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(showgrid=False, linecolor="#c9cfc4", ticks="", fixedrange=True, tickfont=dict(size=11))
    fig.update_yaxes(range=[0, top], dtick=10, ticksuffix=suffix, gridcolor="#e6e8de", zeroline=False,
                     showline=False, ticks="", fixedrange=True, tickfont=dict(size=10.5, color="#5e6f68"))
    return fig
