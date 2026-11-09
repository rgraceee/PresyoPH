"""Model evaluation settings for the CPI forecasting models."""

import pandas as pd

# --- Series ---
TARGET_AREA = "PHILIPPINES"
TARGET_ITEM = "0 - ALL ITEMS"
VARIABLES = ["cpi", "inflation", "purchasing_power"]

DATA_START = pd.Timestamp("2018-01-01")
DATA_END = pd.Timestamp("2026-08-01")

# --- Main evaluation: hold-out test set ---
TEST_MONTHS = 12
TRAIN_END = pd.Timestamp("2025-08-01")
TEST_START = pd.Timestamp("2025-09-01")
TEST_END = DATA_END

TEST_SUBPERIODS = {
    "full test (Sep 2025 - Aug 2026)": (TEST_START, TEST_END),
    "before shock (Sep 2025 - Feb 2026)": (pd.Timestamp("2025-09-01"), pd.Timestamp("2026-02-01")),
    "after shock (Mar 2026 - Aug 2026)": (pd.Timestamp("2026-03-01"), pd.Timestamp("2026-08-01")),
}

# --- Forecast horizon ---
HORIZON = 12
DASHBOARD_HORIZONS = [3, 6, 12]

# --- Rolling-origin evaluation ---
ROLLING_ORIGINS = pd.date_range("2022-08-01", "2024-08-01", freq="6MS")
ROLLING_HORIZON = HORIZON

# --- Model settings ---
PROPOSAL_MODELS = ["ARIMA", "Linear Regression", "Moving Average"]
EXTRA_MODELS = ["ETS"]
ETS_ELIGIBLE_FOR_SELECTION = False

# ARIMA: d = 1 from stationarity checks; p and q chosen by AIC.
ARIMA_D = 1
ARIMA_P_VALUES = [0, 1, 2]
ARIMA_Q_VALUES = [0, 1, 2]
ARIMA_SEASONAL_CANDIDATES = [(0, 0, 0, 0), (1, 0, 0, 12)]

# AIC parsimony rule: candidates within this many AIC points of the lowest
# AIC are equally supported; the fewest-parameter one wins.
AIC_TOLERANCE = 2.0

# Moving Average: window chosen by lowest RMSE on the validation window.
MA_WINDOWS = [3, 6, 12]
VALIDATION_MONTHS = 12

# ETS: additive trend, with or without damping, chosen by AIC.
ETS_DAMPED_OPTIONS = [False, True]

# Prediction intervals shown on the dashboard (95%).
INTERVAL_LEVEL = 0.95

# --- Model-selection rule ---
SELECTION_VARIABLE = "cpi"
SELECTION_BASIS = "pooled"
METRICS = ["MAE", "RMSE", "MAPE"]
TIEBREAK_METRIC = "RMSE"
