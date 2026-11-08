"""
================================================================================
FILE: app/theme.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
This file defines all colours, number formats, and indicator labels used
across the dashboard. It's called a "theme" file because it centralises the
visual style so that charts, cards, and tables look consistent.

If Member 3's design team provides a final colour palette, you only need to
change the values in this one file, and every chart and card picks them up
automatically.

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- app/ui/charts.py: Imports theme for colours (MODEL_COLORS, ACTUAL_COLOR,
  MUTED_COLOR) and number formats (PLOTLY_HOVER_FORMATS, INDICATOR_UNITS).
- app/pages/dashboard.py: Imports theme for format_value(), format_error(),
  INDICATOR_COLORS, INDICATOR_UNITS.
- app/pages/forecasts.py: Imports theme for INDICATOR_NAMES, INDICATOR_SHORT_NAMES,
  INDICATOR_UNITS, format_value(), MODEL_COLORS.
- app/pages/regional.py: Imports theme for INDICATOR_SHORT_NAMES.
- app/pages/trends.py: Does NOT import theme directly (uses app.ui.tokens instead).
- app/components/forecast_charts.py: Imports theme for MODEL_COLORS, ACTUAL_COLOR,
  MUTED_COLOR, PLOTLY_HOVER_FORMATS, INDICATOR_UNITS, format_error().
- app/ui/tokens.py: Has its own copy of INDICATOR_COLORS and MODEL_COLORS
  (kept separate so the Forecasts page's palette is independent).
"""

"""
Colours and number formats shared by the dashboard pages.

The colours are placeholders until Member 3's palette and chart style guide
are ready; replace the values here and every chart picks them up.
"""

# --- Indicator colours ---------------------------------------------------------
# One colour per indicator. These are used in chart lines, KPI cards, and bars.
# The hex codes are dark green (CPI), gold (inflation), orange (purchasing power).

INDICATOR_COLORS = {
    "cpi": "#1B5E4B",           # Dark green for CPI (Consumer Price Index)
    "inflation": "#E9AA2B",     # Gold/yellow for inflation rate
    "purchasing_power": "#EE7B30",  # Orange for purchasing power of the peso
}

# --- Model colours -------------------------------------------------------------
# One consistent colour per model across all forecast charts.
# Used in forecast comparison charts so the same model always has the same colour.

MODEL_COLORS = {
    "ARIMA": "#1B5E4B",         # Dark green for ARIMA model
    "Linear Regression": "#E9AA2B",  # Gold for Linear Regression model
    "Moving Average": "#EE7B30",      # Orange for Moving Average model
    "ETS": "#9CA3AF",           # Grey for ETS model (extra, not in proposal)
}

# --- General chart colours -----------------------------------------------------
# ACTUAL_COLOR: used for actual (historical) data lines in charts.
# MUTED_COLOR: used for secondary elements (reference lines, grid hints, etc.).

ACTUAL_COLOR = "#0F3D36"        # Very dark green/teal for actual historical data lines
MUTED_COLOR = "#9CA3AF"         # Grey for muted/secondary chart elements

# --- Indicator names -----------------------------------------------------------
# Human-readable full names for each indicator (used in titles, headers, labels).

INDICATOR_NAMES = {
    "cpi": "Consumer Price Index",
    "inflation": "Inflation rate",
    "purchasing_power": "Purchasing power of the peso",
}

# --- Short indicator names -----------------------------------------------------
# Short names for buttons and tight spaces (mobile screens, sidebar, etc.).

INDICATOR_SHORT_NAMES = {
    "cpi": "CPI",
    "inflation": "Inflation",
    "purchasing_power": "Purchasing power",
}

# --- Indicator units -----------------------------------------------------------
# Axis titles and plain-language units (what the numbers mean, shown on chart axes).

INDICATOR_UNITS = {
    "cpi": "Index (2018 = 100)",           # CPI is an index where 2018 = 100
    "inflation": "Percent, year on year",  # Inflation is a percentage change vs. same month last year
    "purchasing_power": "Pesos (2018 = ₱1.00)",  # Purchasing power: how much a 2018 peso buys today
}


# --- Value formatting functions ------------------------------------------------
# These functions convert raw numbers into display strings for cards and tables.

def format_value(indicator, value):
    """Format a value as it should appear in cards and tables.

    Different indicators need different formats:
    - CPI: one decimal with thousands separator (e.g. "136.4")
    - Inflation: one decimal with percent sign (e.g. "6.1%")
    - Purchasing power: peso sign with two decimals (e.g. "₱0.73")

    Parameters
    ----------
    indicator : str
        One of "cpi", "inflation", "purchasing_power".
    value : float or None
        The raw numeric value to format.

    Returns
    -------
    str
        Formatted string, or "–" if value is None.
    """
    if value is None:                                    # No data available
        return "–"                                       # Show an en-dash instead of a number
    if indicator == "cpi":                               # CPI format: thousands separator, 1 decimal
        return f"{value:,.1f}"                           # e.g. 136.4 -> "136.4", 1234.5 -> "1,234.5"
    if indicator == "inflation":                         # Inflation format: 1 decimal + percent sign
        return f"{value:.1f}%"                           # e.g. 6.1 -> "6.1%"
    return f"₱{value:.2f}"                               # Purchasing power: peso sign, 2 decimals (e.g. "₱0.73")


def format_error(indicator, value):
    """Format an error size (MAE, RMSE) in the indicator's units.

    Used for forecast error metrics on the Forecasts page.

    Parameters
    ----------
    indicator : str
        One of "cpi", "inflation", "purchasing_power".
    value : float
        The error value to format.

    Returns
    -------
    str
        Formatted error string with unit (pts for CPI, pp for inflation, ₱ for purchasing power).
    """
    if indicator == "cpi":                               # CPI error: 2 decimals + "pts" (points)
        return f"{value:.2f} pts"                        # e.g. 1.5 -> "1.50 pts"
    if indicator == "inflation":                         # Inflation error: 2 decimals + "pp" (percentage points)
        return f"{value:.2f} pp"                         # e.g. 0.5 -> "0.50 pp"
    return f"₱{value:.3f}"                               # Purchasing power error: peso sign, 3 decimals


# --- Plotly hover formats ------------------------------------------------------
# Number formats for Plotly hover tooltips (what shows when you hover over a chart point).

PLOTLY_HOVER_FORMATS = {
    "cpi": ".2f",                                        # CPI: 2 decimal places on hover
    "inflation": ".1f",                                  # Inflation: 1 decimal place on hover
    "purchasing_power": ".2f",                           # Purchasing power: 2 decimal places on hover
}
