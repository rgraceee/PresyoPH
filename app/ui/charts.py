"""
================================================================================
FILE: app/ui/charts.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
This file builds Plotly chart figures for the dashboard screens. All functions
are pure: they take DataFrames as input and return Plotly Figure objects. They
do NOT call Streamlit directly, which means they can be tested independently
and reused across different pages.

Colours come from app.ui.tokens (Figma palette), NOT from app/theme.py. This
keeps the Forecasts page's chart palette independent from the rest of the app.

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- app/pages/dashboard.py: Calls charts.time_series_figure(), charts.forecast_figure().
- app/pages/trends.py: Calls charts.forecast_figure() (via dual_axis_figure which is local).
- app/pages/categories.py: Calls charts.ranked_bar_figure() (via local functions).
- app/pages/forecasts.py: Calls charts.forecast_figure().
- app/theme.py: Provides PLOTLY_HOVER_FORMATS, INDICATOR_UNITS, MUTED_COLOR, ACTUAL_COLOR.
- app/ui/tokens.py: Provides MODEL_COLORS, ACTUAL_COLOR, LINE_PALETTE, HIGHLIGHT_COLOR.
- app/components/forecast_charts.py: Has a similar forecast_figure() but uses theme colours instead of tokens.
- tests/test_forecasts_page.py: Tests charts.forecast_figure(), charts.model_comparison_figure() (via app.components).

================================================================================
"""

"""Plotly figures for the Figma-styled screens. Colours come from app.ui.tokens,
so the Forecasts page's own chart palette (app/theme.py) is not affected."""

import math                                          # math: used for calculating y-axis max in banded_column_figure

import pandas as pd                                  # pandas: DataFrame handling
import plotly.graph_objects as go                    # plotly: interactive chart library

from app import theme                                # theme: shared colours, formats, indicator labels
from app.ui import tokens                            # tokens: Figma colours and styling

# Default layout applied to every chart in this file.
# Controls margins, legend position, fonts, background colours, etc.
LAYOUT = dict(
    template="plotly_white",                         # Clean white background theme
    margin=dict(l=10, r=10, t=40, b=10),             # Small margins: left, right, top, bottom
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11)),  # Horizontal legend at top-right
    hovermode="x unified",                           # Show one hover box for all lines at the same x
    xaxis=dict(showgrid=False, linecolor="#d9ddd3", tickfont=dict(size=11)),  # No vertical grid lines, light axis line
    paper_bgcolor="rgba(0,0,0,0)",                   # Transparent background outside the plot
    plot_bgcolor="rgba(0,0,0,0)",                    # Transparent background inside the plot
    font=dict(family="Nunito Sans, sans-serif", color="#0F3D36", size=12),  # Font family, colour, size
)


def _rgba(color, alpha):
    """Convert a hex colour string to an RGBA string with given alpha.
    
    Parameters
    ----------
    color : str
        Hex colour like "#1B5E4B".
    alpha : float
        Opacity from 0 (transparent) to 1 (opaque).
    
    Returns
    -------
    str
        RGBA string like "rgba(27,94,75,0.18)".
    """
    color = color.lstrip("#")                          # Remove the leading #
    r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))  # Parse red, green, blue from hex pairs
    return f"rgba({r},{g},{b},{alpha})"               # Return RGBA format string


def forecast_figure(history, forecast, variable, model, comparison=None, height=420):
    """Build a forecast chart: actual values, forecast line, and 95% prediction interval.
    
    Shows:
      - Actual (PSA) historical data as a solid line
      - Forecast as a dashed line starting from the last actual point
      - 95% prediction interval as a shaded band
      - Optional comparison models as thin lines
      - A tinted background band for the forecast period
      - "HISTORICAL" / "FORECAST" labels at the split point
    
    Parameters
    ----------
    history : pandas.DataFrame
        Actual data with columns: date, value.
    forecast : pandas.DataFrame
        Forecast data with columns: date, forecast, lower, upper.
    variable : str
        One of "cpi", "inflation", "purchasing_power" (used for hover format and y-axis title).
    model : str
        Model name (used for colour and legend label).
    comparison : dict or None
        Optional {model_name: forecast_dataframe} for comparison lines.
    height : int
        Chart height in pixels.
    
    Returns
    -------
    plotly.graph_objects.Figure
    """
    color = tokens.MODEL_COLORS.get(model, theme.MUTED_COLOR)  # Get colour for this model (or muted if unknown)
    hover = theme.PLOTLY_HOVER_FORMATS[variable]              # Get hover number format for this variable
    fig = go.Figure()                                         # Create empty Plotly figure

    # Trace 1: Upper bound of prediction interval (invisible line, used as fill boundary)
    fig.add_trace(go.Scatter(x=forecast["date"], y=forecast["upper"], mode="lines", line=dict(width=0),
                             showlegend=False, hoverinfo="skip"))
    # Trace 2: Lower bound filled up to upper bound, creating a shaded band
    fig.add_trace(go.Scatter(x=forecast["date"], y=forecast["lower"], mode="lines", line=dict(width=0),
                             fill="tonexty", fillcolor=_rgba(color, 0.18), name="95% prediction interval",
                             hoverinfo="skip"))
    # Trace 3: Actual historical data
    fig.add_trace(go.Scatter(x=history["date"], y=history["value"], mode="lines", name="Actual (PSA)",
                             line=dict(color=tokens.ACTUAL_COLOR, width=2),
                             hovertemplate=f"%{{y:{hover}}}<extra>Actual</extra>"))
    # Join the last actual point to the first forecast point so the line is continuous
    last = history.iloc[[-1]].rename(columns={"value": "forecast"})
    joined = pd.concat([last[["date", "forecast"]], forecast[["date", "forecast"]]])
    # Trace 4: Forecast line (dashed, starting from last actual)
    fig.add_trace(go.Scatter(x=joined["date"], y=joined["forecast"], mode="lines+markers", name=f"Forecast ({model})",
                             line=dict(color=color, width=2.5, dash="dash"), marker=dict(size=5),
                             hovertemplate=f"%{{y:{hover}}}<extra>Forecast</extra>"))
    # Trace 5+: Optional comparison models (thin, semi-transparent lines)
    for name, other in (comparison or {}).items():
        fig.add_trace(go.Scatter(x=other["date"], y=other["forecast"], mode="lines", name=name,
                                 line=dict(color=tokens.MODEL_COLORS.get(name, theme.MUTED_COLOR), width=1.2),
                                 opacity=0.8, hovertemplate=f"%{{y:{hover}}}<extra>{name}</extra>"))
    # Figma styling: tinted band for forecast period, HISTORICAL/FORECAST labels
    split = history["date"].iloc[-1]                         # Last actual date = split point
    fig.add_vrect(x0=split, x1=forecast["date"].iloc[-1], fillcolor="rgba(247,185,39,0.10)", line_width=0, layer="below")
    fig.add_vline(x=split, line=dict(color=theme.MUTED_COLOR, dash="dot", width=1))
    for text, anchor, x in (("HISTORICAL", "right", split), ("FORECAST", "left", split)):
        fig.add_annotation(x=x, y=1.0, yref="paper", text=text, showarrow=False, xanchor=anchor, yanchor="top",
                           font=dict(size=10, color="#7a8a84"), xshift=-6 if anchor == "right" else 6)
    fig.update_layout(**LAYOUT, height=height, yaxis_title=theme.INDICATOR_UNITS[variable])  # Apply layout + height + y-axis title
    fig.update_yaxes(gridcolor="#e8e8de", zeroline=False)    # Light grid lines, no zero line
    return fig                                               # Return the completed figure


def time_series_figure(frame, colors=None, y_title=None, hover=".2f", height=360, y_suffix=""):
    """Build a multi-line time series chart.
    
    The frame is "wide" format: indexed by date, with one column per line.
    Used for comparing multiple categories or areas on one chart.
    
    Parameters
    ----------
    frame : pandas.DataFrame
        Indexed by date, one column per line to plot.
    colors : dict or None
        Optional {column_name: colour} mapping.
    y_title : str or None
        Y-axis title.
    hover : str
        Number format string for hover tooltips.
    height : int
        Chart height in pixels.
    y_suffix : str
        Suffix added to y-axis values (e.g. "%").
    
    Returns
    -------
    plotly.graph_objects.Figure
    """
    fig = go.Figure()                                        # Create empty figure
    for i, column in enumerate(frame.columns):               # One trace per column
        color = (colors or {}).get(column, tokens.LINE_PALETTE[i % len(tokens.LINE_PALETTE)])  # Colour from param or palette
        fig.add_trace(go.Scatter(
            x=frame.index, y=frame[column],
            mode="lines+markers" if len(frame) <= 30 else "lines",  # Markers for short series, lines only for long
            name=str(column),                                # Legend label = column name
            line=dict(color=color, width=2.5),
            marker=dict(size=6),
            hovertemplate=f"%{{y:{hover}}}{y_suffix}<extra>{column}</extra>",
        ))
    fig.update_layout(**LAYOUT, height=height, showlegend=len(frame.columns) > 1)  # Show legend only if multiple lines
    fig.update_yaxes(title=y_title, ticksuffix=y_suffix, gridcolor="#e8e8de", zeroline=False)
    fig.update_xaxes(title=None)                             # No x-axis title (dates are self-explanatory)
    return fig


def ranked_bar_figure(labels, values, reference=None, reference_label="Philippines",
                      color="#2563EB", highlight=None, hover=".1f", suffix="", height=None):
    """Build a horizontal bar chart with bars ranked highest at top.
    
    Parameters
    ----------
    labels : list of str
        Category labels (y-axis).
    values : list of float
        Bar values (x-axis).
    reference : float or None
        If provided, draw a vertical reference line (e.g. national average).
    reference_label : str
        Label for the reference line.
    color : str
        Default bar colour (hex).
    highlight : str or None
        If provided, this label gets the highlight colour.
    hover : str
        Number format for hover.
    suffix : str
        Suffix for values (e.g. "%").
    height : int or None
        Chart height. Auto-calculated if None.
    
    Returns
    -------
    plotly.graph_objects.Figure
    """
    colors = [tokens.HIGHLIGHT_COLOR if label == highlight else color for label in labels]  # Highlight one bar if specified
    fig = go.Figure(go.Bar(
        x=list(values), y=list(labels), orientation="h", marker_color=colors,
        hovertemplate=f"%{{y}}<br>%{{x:{hover}}}{suffix}<extra></extra>",
    ))
    if reference is not None:                                # Add vertical reference line if provided
        fig.add_vline(x=reference, line_dash="dot", line_color=tokens.ACTUAL_COLOR,
                      annotation_text=f"{reference_label}: {reference:{hover}}{suffix}",
                      annotation_position="top")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=LAYOUT["font"],
        template="plotly_white", margin=dict(l=10, r=10, t=40, b=10), showlegend=False,
        height=height or max(300, 30 * len(labels) + 80),    # Auto-height based on number of bars
    )
    fig.update_yaxes(autorange="reversed", title=None)       # Highest value at top
    fig.update_xaxes(ticksuffix=suffix, title=None)
    return fig


def grouped_bar_figure(categories, series, colors, y_title=None, hover=".1f", height=380):
    """Build grouped vertical bars (one group per category, one bar per series).
    
    Parameters
    ----------
    categories : list
        Category names (x-axis).
    series : dict of {name: list of values}
        One entry per bar series (e.g. income, expenditure, savings).
    colors : dict of {name: colour}
        Colour for each series.
    y_title : str or None
        Y-axis title.
    hover : str
        Number format for hover.
    height : int
        Chart height.
    
    Returns
    -------
    plotly.graph_objects.Figure
    """
    fig = go.Figure()
    for name, values in series.items():                      # One trace per series
        fig.add_trace(go.Bar(
            x=list(categories), y=list(values), name=name, marker_color=colors.get(name),
            hovertemplate=f"%{{y:{hover}}}<extra>{name}</extra>",
        ))
    fig.update_layout(**{**LAYOUT, "hovermode": "x unified"}, barmode="group", height=height)  # Group bars side by side
    fig.update_yaxes(title=y_title)
    return fig


def column_figure(categories, values, color, y_title=None, suffix="", hover=".1f", height=320):
    """Build a simple vertical column chart (one colour for all bars).
    
    Parameters
    ----------
    categories : list
        Category names (x-axis).
    values : list of float
        Bar values (y-axis).
    color : str
        Bar colour (hex).
    y_title : str or None
        Y-axis title.
    suffix : str
        Value suffix (e.g. "%").
    hover : str
        Number format for hover.
    height : int
        Chart height.
    
    Returns
    -------
    plotly.graph_objects.Figure
    """
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
    """Build rounded column charts with bars coloured in 4 bands by rank.
    
    Used for FIES savings rate by decile, regional rankings, etc.
    The categories keep their given order; only colours depend on rank.
    
    Parameters
    ----------
    categories : list
        Category names (x-axis).
    values : list of float
        Bar values (y-axis).
    suffix : str
        Value suffix (e.g. "%").
    hover : str
        Number format for hover.
    height : int
        Chart height.
    higher_is_better : bool
        If True, highest value gets the best colour. If False, lowest gets best.
    
    Returns
    -------
    plotly.graph_objects.Figure
    """
    values = [float(v) for v in values]                      # Ensure all values are floats
    n = len(values)
    # Sort indices by value to determine rank (best first if higher_is_better)
    best_first = sorted(range(n), key=lambda i: values[i], reverse=higher_is_better)
    colors = [""] * n
    for rank, i in enumerate(best_first):                    # Assign band colours by rank
        colors[i] = BAND_COLORS[min(len(BAND_COLORS) - 1, rank * len(BAND_COLORS) // n)]
    top = max(10, math.ceil((max(values) + 4) / 10) * 10)   # Calculate y-axis max (round up to nearest 10)

    fig = go.Figure(go.Bar(
        x=list(categories), y=values, marker_color=colors,
        text=[f"{v:.0f}{suffix}" for v in values],           # Value labels above each bar
        textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color="#0d3e3b"),
        hovertemplate=f"%{{x}}<br>%{{y:{hover}}}{suffix}<extra></extra>",
    ))
    try:
        fig.update_traces(marker_cornerradius=6)             # Rounded bar tops (Plotly 5.24+)
    except ValueError:
        pass                                                 # Older Plotly versions don't support this
    fig.update_layout(
        template="plotly_white", height=height, bargap=0.3, showlegend=False,
        margin=dict(l=36, r=6, t=22, b=30), font=LAYOUT["font"],
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(showgrid=False, linecolor="#c9cfc4", ticks="", fixedrange=True, tickfont=dict(size=11))
    fig.update_yaxes(range=[0, top], dtick=10, ticksuffix=suffix, gridcolor="#e6e8de", zeroline=False,
                     showline=False, ticks="", fixedrange=True, tickfont=dict(size=10.5, color="#5e6f68"))
    return fig
