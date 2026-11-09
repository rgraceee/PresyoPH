"""Figma colours, notes, and shared wording for the PresyoPH UI."""

INDICATOR_COLORS = {"cpi": "#1B5E4B", "inflation": "#E9AA2B", "purchasing_power": "#EE7B30"}

MODEL_COLORS = {"ARIMA": "#1B5E4B", "Linear Regression": "#E9AA2B", "Moving Average": "#EE7B30", "ETS": "#9CA3AF"}

ACTUAL_COLOR = "#0F3D36"

FIES_COLORS = {"income": "#1B5E4B", "expenditure": "#E9AA2B", "savings": "#EE7B30"}

LINE_PALETTE = ["#1B5E4B", "#E9AA2B", "#EE7B30", "#D94B3D", "#6FA06B", "#0891B2", "#7C3AED", "#6B7280"]

RANK_COLORS = ["#1B5E4B", "#6FA06B", "#E9AA2B", "#EE7B30", "#D94B3D"]

HIGHLIGHT_COLOR = "#D94B3D"

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

DECILE_LONG = {**DECILE_SHORT, "First Decile": "Bottom 10% (lowest income)", "Tenth Decile": "Top 10% (highest income)"}

INCOME_RANK_AXIS = "Families ranked by income (lowest → highest)"

FIES_NOTE = (
    "**FIES is a 2023 snapshot.** The Family Income and Expenditure Survey is not a monthly series, so these "
    "figures show how families of different income levels compare in 2023. They are not trends and are not "
    "forecast. Families are ranked by income and split into ten equal groups, from the bottom 10% of earners to "
    "the top 10%."
)

PSA_ATTRIBUTION = "Source: Philippine Statistics Authority (PSA), OpenSTAT, via statistics.bettergov.ph."

FORECAST_DISCLAIMER = (
    "Forecasts are statistical estimates based only on historical CPI patterns. They do not account for fuel "
    "prices, weather, disasters, policy changes, or other unexpected events."
)
