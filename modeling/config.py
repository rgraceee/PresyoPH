"""
================================================================================
FILE: modeling/config.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
This file is the central configuration for the CPI forecasting models
(task 2 of the project). Every modeling script reads its settings from here,
so a change to the data split, forecast horizon, or model selection rule only
has to be made in one place.

Settings include:
  - Target series: national all-items CPI (option B - only CPI is modeled)
  - Data period: Jan 2018 to Aug 2026
  - Train/test split: 88 months train, 12 months test
  - Forecast horizon: 12 months
  - Rolling-origin evaluation: 5 origins, 6 months apart
  - Model settings: ARIMA orders, MA windows, ETS options
  - Model selection rule: 2-of-3-metrics wins, else lowest RMSE

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- modeling/evaluation.py: Imports config for HORIZON, VARIABLES, PROPOSAL_MODELS,
  EXTRA_MODELS, ETS_ELIGIBLE_FOR_SELECTION, ARIMA_*, MA_WINDOWS, VALIDATION_MONTHS,
  ETS_DAMPED_OPTIONS, INTERVAL_LEVEL, SELECTION_VARIABLE, SELECTION_BASIS,
  METRICS, TIEBREAK_METRIC, ROLLING_ORIGINS, ROLLING_HORIZON, TEST_SUBPERIODS,
  TRAIN_END, TEST_START, TEST_END, DATA_START, DATA_END, TARGET_AREA, TARGET_ITEM.
- modeling/derive.py: No direct import (but uses same formulas).
- modeling/models.py: Imports config for HORIZON, INTERVAL_LEVEL, ARIMA_D,
  ARIMA_P_VALUES, ARIMA_Q_VALUES, ARIMA_SEASONAL_CANDIDATES, AIC_TOLERANCE,
  MA_WINDOWS, VALIDATION_MONTHS, ETS_DAMPED_OPTIONS.
- modeling/run_pipeline.py: Imports config for VARIABLES, DATA_END, TRAIN_END,
  TEST_START, TEST_END, HORIZON, DASHBOARD_HORIZONS, INTERVAL_LEVEL,
  SELECTION_VARIABLE, SELECTION_BASIS, TEST_SUBPERIODS, ROLLING_ORIGINS,
  TARGET_AREA, TARGET_ITEM.
- backend/data.py: Does NOT import config (uses its own FORECAST_HORIZONS).

================================================================================
"""

"""Evaluation setup for the CPI forecasting models (task 2).

Every modeling script reads its settings from here, so a change to the split,
horizon, or selection rule only has to be made in one place.
"""

import pandas as pd                                  # pandas: Timestamp for dates

# --- Series ------------------------------------------------------------------
# Only national all-items CPI is modeled (option B). Forecasted inflation and
# purchasing power are derived from the CPI forecast (see modeling/derive.py)
# and scored against PSA's published series.
TARGET_AREA = "PHILIPPINES"                          # National level only
TARGET_ITEM = "0 - ALL ITEMS"                        # All items (aggregate)
VARIABLES = ["cpi", "inflation", "purchasing_power"]  # All three variables are forecast (CPI directly, others derived)

DATA_START = pd.Timestamp("2018-01-01")              # First month of data
DATA_END = pd.Timestamp("2026-08-01")                # Last month of data

# --- Main evaluation: hold-out test set --------------------------------------
# The most recent 12 months are withheld from training (about 88/12 split).
# The test size matches the 12-month forecast horizon and covers one full
# seasonal cycle, so every calendar month is scored once.
TEST_MONTHS = 12
TRAIN_END = pd.Timestamp("2025-08-01")               # Last training month
TEST_START = pd.Timestamp("2025-09-01")              # First test month
TEST_END = DATA_END                                  # Last test month

# Sub-periods reported alongside the full test period, because of the price
# shock in March-April 2026 (see notebooks/01_exploratory_checks.ipynb).
TEST_SUBPERIODS = {
    "full test (Sep 2025 - Aug 2026)": (TEST_START, TEST_END),
    "before shock (Sep 2025 - Feb 2026)": (pd.Timestamp("2025-09-01"), pd.Timestamp("2026-02-01")),
    "after shock (Mar 2026 - Aug 2026)": (pd.Timestamp("2026-03-01"), pd.Timestamp("2026-08-01")),
}

# --- Forecast horizon --------------------------------------------------------
# Each model forecasts 12 months ahead from its origin. The dashboard's 3- and
# 6-month views are the first 3 and 6 months of the same forecast.
HORIZON = 12
DASHBOARD_HORIZONS = [3, 6, 12]                      # Horizons shown on dashboard

# --- Rolling-origin evaluation -----------------------------------------------
# Expanding-window evaluation on earlier periods, so the model choice does not
# depend on one unusual test period. Its folds are pooled with the main test
# for model selection. Each origin is the last training month; the model then
# forecasts the next 12 months. All folds end before the main test set starts,
# so the test set stays unseen: five origins, six months apart, from Aug 2022
# (56 training months, forecasting Sep 2022 - Aug 2023) to Aug 2024 (80 training
# months, forecasting Sep 2024 - Aug 2025).
ROLLING_ORIGINS = pd.date_range("2022-08-01", "2024-08-01", freq="6MS")
ROLLING_HORIZON = HORIZON

# --- Model settings ----------------------------------------------------------
# Models named in the proposal. ETS is run and reported as a clearly labelled
# extra; it becomes eligible for selection only once the instructor approves
# adding it.
PROPOSAL_MODELS = ["ARIMA", "Linear Regression", "Moving Average"]
EXTRA_MODELS = ["ETS"]
ETS_ELIGIBLE_FOR_SELECTION = False

# ARIMA: d = 1 and D = 0 from the stationarity checks; p and q chosen by AIC
# (with the parsimony rule below). One seasonal candidate is included only to
# confirm seasonality is not needed.
ARIMA_D = 1                                          # First differencing (make series stationary)
ARIMA_P_VALUES = [0, 1, 2]                           # AR orders to try
ARIMA_Q_VALUES = [0, 1, 2]                           # MA orders to try
ARIMA_SEASONAL_CANDIDATES = [(0, 0, 0, 0), (1, 0, 0, 12)]  # No seasonality vs. seasonal (12-month)

# Candidates within this many AIC points of the lowest AIC are treated as
# equally supported by the data, and the one with the fewest parameters is
# chosen (Burnham & Anderson, 2002). Applies to ARIMA and ETS.
AIC_TOLERANCE = 2.0

# Moving Average: window k chosen by lowest RMSE on the last 12 training months
# (validation window), using only data before that window to forecast it.
MA_WINDOWS = [3, 6, 12]                              # Window sizes to try (in months)
VALIDATION_MONTHS = 12                               # Months used for MA validation

# ETS: additive trend, with or without damping, chosen by AIC (with the
# parsimony rule above).
ETS_DAMPED_OPTIONS = [False, True]

# Prediction intervals shown on the dashboard (95%).
INTERVAL_LEVEL = 0.95

# --- Model-selection rule ----------------------------------------------------
# One final model is selected, on its CPI forecasts:
#   1. A model that has the lowest error on at least 2 of the 3 metrics wins.
#   2. Otherwise, the model with the lowest RMSE wins.
# Inflation and purchasing power are then derived from that model's CPI
# forecast, so the three dashboard forecasts always agree with each other.
# Metrics for all three variables are still computed and reported. Note that
# MAPE for inflation is unstable because test-period inflation is as low as
# 1.5%, so a small miss becomes a large percentage error.
#
# The rule is applied to the pooled forecasts from all six origins: the main
# test origin (Aug 2025) and the five rolling-origin folds, 72 forecast months
# per model. This was changed after the results were seen. Originally the main
# 12-month test alone decided, with rolling origin as a check only. On the main
# test alone, Linear Regression wins, largely because the March-April 2026
# price shock lifted actual CPI up to its forecasts, which had been too high
# before the shock. The pooled evaluation, which favours ARIMA, depends less on
# that single period. Both results are reported in notebooks/03_evaluation.ipynb,
# and the change must be disclosed in the paper.
#
# The final model is refit on all data with the same specification that was
# evaluated; no extra terms are added for the 2026 price shock.
SELECTION_VARIABLE = "cpi"                           # Model selection is based on CPI only
SELECTION_BASIS = "pooled"                           # "pooled" (all six origins) or "main_test"
METRICS = ["MAE", "RMSE", "MAPE"]                    # Error metrics
TIEBREAK_METRIC = "RMSE"                             # Tiebreaker if no model wins 2 of 3
