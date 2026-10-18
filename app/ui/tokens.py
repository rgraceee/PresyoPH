"""Figma colours, notes, and shared wording for the PresyoPH UI.

Kept separate from app/theme.py so the Forecasts page's chart palette (owned by
the modeling side) is untouched. Everything here is used only by app/ui and the
new pages.
"""

# One colour per indicator, from the Figma palette.
INDICATOR_COLORS = {"cpi": "#1B5E4B", "inflation": "#E9AA2B", "purchasing_power": "#EE7B30"}
MODEL_COLORS = {"ARIMA": "#1B5E4B", "Linear Regression": "#E9AA2B", "Moving Average": "#EE7B30", "ETS": "#9CA3AF"}
ACTUAL_COLOR = "#0F3D36"

# FIES charts: one colour per measure.
FIES_COLORS = {"income": "#1B5E4B", "expenditure": "#E9AA2B", "savings": "#EE7B30"}

# Lines for several categories or regions on one chart.
LINE_PALETTE = ["#1B5E4B", "#E9AA2B", "#EE7B30", "#D94B3D", "#6FA06B", "#0891B2", "#7C3AED", "#6B7280"]

# Ranking colours (higher value to lower value), as in the Figma regional chart.
RANK_COLORS = ["#1B5E4B", "#6FA06B", "#E9AA2B", "#EE7B30", "#D94B3D"]

HIGHLIGHT_COLOR = "#D94B3D"

DECILE_SHORT = {
    "All Income Groups": "All",
    "First Decile": "1st (lowest)",
    "Second Decile": "2nd",
    "Third Decile": "3rd",
    "Fourth Decile": "4th",
    "Fifth Decile": "5th",
    "Sixth Decile": "6th",
    "Seventh Decile": "7th",
    "Eighth Decile": "8th",
    "Ninth Decile": "9th",
    "Tenth Decile": "10th (highest)",
}

FIES_NOTE = (
    "**FIES is a 2023 snapshot.** The Family Income and Expenditure Survey is not a monthly series, so these "
    "figures show how families of different income levels compare in 2023. They are not trends and are not "
    "forecast. Each income group (decile) is one tenth of families, from the lowest-income tenth to the highest."
)

PSA_ATTRIBUTION = "Source: Philippine Statistics Authority (PSA), OpenSTAT, via statistics.bettergov.ph."
FORECAST_DISCLAIMER = (
    "Forecasts are statistical estimates based only on historical CPI patterns. They do not account for fuel "
    "prices, weather, disasters, policy changes, or other unexpected events."
)
