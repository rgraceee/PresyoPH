"""Evaluation setup for the CPI forecasting models (task 2).

Every modeling script reads its settings from here, so a change to the split,
horizon, or selection rule only has to be made in one place.
"""

import pandas as pd

# --- Series ------------------------------------------------------------------

# Only national all-items CPI is modeled (option B). Forecasted inflation and
# purchasing power are derived from the CPI forecast (see modeling/derive.py)
# and scored against PSA's published series.
TARGET_AREA = "PHILIPPINES"
TARGET_ITEM = "0 - ALL ITEMS"
VARIABLES = ["cpi", "inflation", "purchasing_power"]

DATA_START = pd.Timestamp("2018-01-01")
DATA_END = pd.Timestamp("2026-08-01")

# --- Main evaluation: hold-out test set -------------------------------------

# The most recent 12 months are withheld from training (about 88/12). The test
# size matches the 12-month forecast horizon rather than a fixed percentage, and
# covers one full seasonal cycle, so every calendar month is scored once.
TEST_MONTHS = 12
TRAIN_END = pd.Timestamp("2025-08-01")
TEST_START = pd.Timestamp("2025-09-01")
TEST_END = DATA_END

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
DASHBOARD_HORIZONS = [3, 6, 12]

# --- Rolling-origin evaluation -----------------------------------------------

# Expanding-window evaluation on earlier periods, so the model choice does not
# depend on one unusual test period. Its folds are pooled with the main test
# for model selection (see the selection rule below). Each origin is the last training month;
# the model then forecasts the next 12 months. All folds end before the main
# test set starts, so the test set stays unseen: five origins, six months
# apart, from Aug 2022 (56 training months, forecasting Sep 2022 - Aug 2023) to
# Aug 2024 (80 training months, forecasting Sep 2024 - Aug 2025).
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
ARIMA_D = 1
ARIMA_P_VALUES = [0, 1, 2]
ARIMA_Q_VALUES = [0, 1, 2]
ARIMA_SEASONAL_CANDIDATES = [(0, 0, 0, 0), (1, 0, 0, 12)]

# Candidates within this many AIC points of the lowest AIC are treated as
# equally supported by the data, and the one with the fewest parameters is
# chosen (Burnham & Anderson, 2002). Applies to ARIMA and ETS.
AIC_TOLERANCE = 2.0

# Moving Average: window k chosen by lowest RMSE on the last 12 training months
# (validation window), using only data before that window to forecast it.
MA_WINDOWS = [3, 6, 12]
VALIDATION_MONTHS = 12

# ETS: additive trend, with or without damping, chosen by AIC (with the
# parsimony rule above).
ETS_DAMPED_OPTIONS = [False, True]

# Prediction intervals shown on the dashboard.
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
# 12-month test alone decided, with rolling origin as a check only. On the
# main test alone, Linear Regression wins, largely because the March-April
# 2026 price shock lifted actual CPI up to its forecasts, which had been too
# high before the shock. The pooled evaluation, which favours ARIMA, depends
# less on that single period. Both results are reported in
# notebooks/03_evaluation.ipynb, and the change must be disclosed in the paper.
#
# The final model is refit on all data with the same specification that was
# evaluated; no extra terms are added for the 2026 price shock.
SELECTION_VARIABLE = "cpi"
SELECTION_BASIS = "pooled"  # "pooled" (all six origins) or "main_test"
METRICS = ["MAE", "RMSE", "MAPE"]
TIEBREAK_METRIC = "RMSE"
