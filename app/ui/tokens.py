"""
================================================================================
FILE: app/ui/tokens.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
This file defines Figma colours, notes, and shared wording for the PresyoPH UI.
It's kept separate from app/theme.py so that the Forecasts page's chart palette
(owned by the modeling side) is independent from the rest of the app.

Everything here is used only by app/ui and the new pages.

Contents:
  - INDICATOR_COLORS: one colour per indicator (from Figma palette)
  - MODEL_COLORS: one colour per forecast model
  - ACTUAL_COLOR: colour for actual historical data lines
  - FIES_COLORS: one colour per FIES measure (income, expenditure, savings)
  - LINE_PALETTE: colours for multi-line charts
  - RANK_COLORS: colours for ranked lists (best to worst)
  - HIGHLIGHT_COLOR: colour for highlighted items
  - DECILE_SHORT / DECILE_LONG: short and long names for FIES income deciles
  - INCOME_RANK_AXIS: axis label for income decile charts
  - FIES_NOTE: explanatory text about FIES being a 2023 snapshot
  - PSA_ATTRIBUTION: source attribution text
  - FORECAST_DISCLAIMER: disclaimer about forecast limitations

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- app/ui/shell.py: Uses tokens.RANK_COLORS, tokens.PSA_ATTRIBUTION, tokens.FORECAST_DISCLAIMER.
- app/ui/charts.py: Uses tokens.MODEL_COLORS, tokens.ACTUAL_COLOR, tokens.LINE_PALETTE,
  tokens.HIGHLIGHT_COLOR.
- app/pages/dashboard.py: Uses tokens.DECILE_SHORT.
- app/pages/finances.py: Uses tokens.DECILE_SHORT, tokens.DECILE_LONG, tokens.FIES_COLORS,
  tokens.INCOME_RANK_AXIS, tokens.FIES_NOTE.
- app/pages/reports.py: Uses tokens.DECILE_SHORT.
- backend/data.py: Does NOT import tokens (uses its own INDICATOR_LABELS).

================================================================================
"""

"""Figma colours, notes, and shared wording for the PresyoPH UI.

Kept separate from app/theme.py so the Forecasts page's chart palette (owned by
the modeling side) is untouched. Everything here is used only by app/ui and the
new pages.
"""

# --- Colours -------------------------------------------------------------------
# One colour per indicator, from the Figma palette.
INDICATOR_COLORS = {"cpi": "#1B5E4B", "inflation": "#E9AA2B", "purchasing_power": "#EE7B30"}

# One consistent colour per model across all forecast charts.
MODEL_COLORS = {"ARIMA": "#1B5E4B", "Linear Regression": "#E9AA2B", "Moving Average": "#EE7B30", "ETS": "#9CA3AF"}

# Colour for actual (historical) data lines in charts.
ACTUAL_COLOR = "#0F3D36"

# FIES charts: one colour per measure (income, expenditure, savings).
FIES_COLORS = {"income": "#1B5E4B", "expenditure": "#E9AA2B", "savings": "#EE7B30"}

# Lines for several categories or regions on one chart (8 colours).
LINE_PALETTE = ["#1B5E4B", "#E9AA2B", "#EE7B30", "#D94B3D", "#6FA06B", "#0891B2", "#7C3AED", "#6B7280"]

# Ranking colours (higher value to lower value), as in the Figma regional chart.
RANK_COLORS = ["#1B5E4B", "#6FA06B", "#E9AA2B", "#EE7B30", "#D94B3D"]

# Colour for highlighted items (e.g. selected region in a ranking).
HIGHLIGHT_COLOR = "#D94B3D"

# --- FIES decile labels --------------------------------------------------------
# FIES deciles named by where families rank by income, e.g. "10–20%" is the second-lowest tenth.
# Short names for use in charts and tight spaces.
DECILE_SHORT = {
    "All Income Groups": "All families",
    "First Decile": "Bottom 10%",
    "Second Decile": "10–20%",
    "Third Decile": "20–30%",
    "Fourth Decile": "30–40%",
    "Fifth Decile": "40–50%",
    "Sixth Decile": "50–60%",
    "Seventh Decile": "60–70%",
    "Eighth Decile": "70–80%",
    "Ninth Decile": "80–90%",
    "Tenth Decile": "Top 10%",
}

# Longer form for dropdowns and headings, where there is room to say which end is which.
# Adds clarification like "(lowest income)" and "(highest income)".
DECILE_LONG = {**DECILE_SHORT, "First Decile": "Bottom 10% (lowest income)", "Tenth Decile": "Top 10% (highest income)"}

# Axis label for income decile charts.
INCOME_RANK_AXIS = "Families ranked by income (lowest → highest)"

# --- Explanatory text ----------------------------------------------------------
# Note explaining that FIES is a 2023 snapshot, not a trend or forecast.
FIES_NOTE = (
    "**FIES is a 2023 snapshot.** The Family Income and Expenditure Survey is not a monthly series, so these "
    "figures show how families of different income levels compare in 2023. They are not trends and are not "
    "forecast. Families are ranked by income and split into ten equal groups, from the bottom 10% of earners to "
    "the top 10%."
)

# Source attribution shown in the footer of every page.
PSA_ATTRIBUTION = "Source: Philippine Statistics Authority (PSA), OpenSTAT, via statistics.bettergov.ph."

# Forecast disclaimer shown in the footer of every page.
FORECAST_DISCLAIMER = (
    "Forecasts are statistical estimates based only on historical CPI patterns. They do not account for fuel "
    "prices, weather, disasters, policy changes, or other unexpected events."
)
