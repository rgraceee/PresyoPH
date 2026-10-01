"""Colours and number formats shared by the dashboard pages.

The colours are placeholders until Member 3's palette and chart style guide
are ready; replace the values here and every chart picks them up.
"""

# One colour per indicator (style guide: "one color per indicator").
INDICATOR_COLORS = {
    "cpi": "#2563EB",
    "inflation": "#DC2626",
    "purchasing_power": "#059669",
}

# One colour per model. The selected model is drawn in its indicator's colour
# on forecast charts; these are used where models are compared.
MODEL_COLORS = {
    "ARIMA": "#2563EB",
    "Linear Regression": "#D97706",
    "Moving Average": "#7C3AED",
    "ETS": "#6B7280",
}

ACTUAL_COLOR = "#111827"
MUTED_COLOR = "#9CA3AF"

INDICATOR_NAMES = {
    "cpi": "Consumer Price Index",
    "inflation": "Inflation rate",
    "purchasing_power": "Purchasing power of the peso",
}

# Short names for buttons and other tight spaces (fit on a phone screen).
INDICATOR_SHORT_NAMES = {
    "cpi": "CPI",
    "inflation": "Inflation",
    "purchasing_power": "Purchasing power",
}

# Axis titles and plain-language units.
INDICATOR_UNITS = {
    "cpi": "Index (2018 = 100)",
    "inflation": "Percent, year on year",
    "purchasing_power": "Pesos (2018 = ₱1.00)",
}


def format_value(indicator, value):
    """A value as it should appear in cards and tables."""
    if value is None:
        return "–"
    if indicator == "cpi":
        return f"{value:,.1f}"
    if indicator == "inflation":
        return f"{value:.1f}%"
    return f"₱{value:.2f}"


def format_error(indicator, value):
    """An error size (MAE, RMSE) in the indicator's units."""
    if indicator == "cpi":
        return f"{value:.2f} pts"
    if indicator == "inflation":
        return f"{value:.2f} pp"
    return f"₱{value:.3f}"


# Number formats for st.column_config / Plotly hover text.
VALUE_FORMATS = {"cpi": "%.2f", "inflation": "%.1f%%", "purchasing_power": "₱%.2f"}
PLOTLY_HOVER_FORMATS = {"cpi": ".2f", "inflation": ".1f", "purchasing_power": ".2f"}
