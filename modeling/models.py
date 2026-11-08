"""
================================================================================
FILE: modeling/models.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
This file implements the CPI forecasting models (task 3). Four models are
available:

  1. ARIMA(p, 1, q) with optional seasonal component - autoregressive integrated
     moving average, orders chosen by AIC with parsimony rule
  2. Linear Regression - CPI regressed on a time index (trend), fitted with OLS
  3. Moving Average - flat forecast equal to the mean of the last k months,
     where k is chosen by validation RMSE
  4. ETS (Exponential Smoothing) - Holt's method with optional damped trend,
     chosen by AIC (extra model, not in the original proposal)

Every model is a function with the same signature:
    fit_<model>(train, horizon) -> ForecastResult

Each function tunes the model on `train` only (no future data leakage), so it
can be called from any origin: main test set, rolling-origin folds, or final
forecast.

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- modeling/config.py: Imports config for HORIZON, INTERVAL_LEVEL, ARIMA_D,
  ARIMA_P_VALUES, ARIMA_Q_VALUES, ARIMA_SEASONAL_CANDIDATES, AIC_TOLERANCE,
  MA_WINDOWS, VALIDATION_MONTHS, ETS_DAMPED_OPTIONS.
- modeling/evaluation.py: Imports fit_all() from this file.
- modeling/run_pipeline.py: Does NOT import directly (evaluation.py does).
- backend/data.py: Does NOT import models (forecasting happens in modeling layer).

================================================================================
"""

"""CPI forecasting models (task 3).

Every model is a function with the same signature:

    fit_<model>(train, horizon) -> ForecastResult

`train` is the monthly CPI history up to the forecast origin and `horizon` is
the number of months to forecast after it. Each function tunes the model on
`train` only, so it can be called from any origin, for the main test set, for
every rolling-origin fold, and for the final forecast, without seeing future
data.
"""

import itertools                                      # itertools: combinations of model parameters
import warnings                                       # warnings: catch convergence warnings
from dataclasses import dataclass, field              # dataclass: ForecastResult container

import numpy as np                                    # numpy: numerical operations
import pandas as pd                                   # pandas: Series, DataFrame
import statsmodels.api as sm                          # statsmodels: OLS for Linear Regression
from statsmodels.tools.sm_exceptions import ConvergenceWarning  # statsmodels: warning type
from statsmodels.tsa.arima.model import ARIMA         # statsmodels: ARIMA model
from statsmodels.tsa.exponential_smoothing.ets import ETSModel  # statsmodels: ETS model

from modeling import config                           # config: model settings


@dataclass
class ForecastResult:
    """Container for a single model's forecast result.
    
    Attributes
    ----------
    model : str
        Model name.
    forecast : pandas.Series
        Point forecasts indexed by date.
    lower : pandas.Series
        Lower bound of prediction interval.
    upper : pandas.Series
        Upper bound of prediction interval.
    params : dict
        Model parameters (order, drift, etc.).
    candidates : pandas.DataFrame
        Tuning candidates (one row per candidate tried).
    fitted : object
        The fitted statsmodels result object (for diagnostics).
    """
    model: str
    forecast: pd.Series
    lower: pd.Series
    upper: pd.Series
    params: dict = field(default_factory=dict)
    candidates: pd.DataFrame = field(default_factory=pd.DataFrame)
    fitted: object = None

    def to_frame(self):
        """Convert to a DataFrame with model, forecast, lower, upper columns."""
        return pd.DataFrame({
            "model": self.model,
            "forecast": self.forecast,
            "lower": self.lower,
            "upper": self.upper,
        })


def _future_index(train, horizon):
    """Generate month-start dates for the forecast period.
    
    Parameters
    ----------
    train : pandas.Series
        Training data indexed by date.
    horizon : int
        Number of months to forecast.
    
    Returns
    -------
    pandas.DatetimeIndex
        Month-start dates starting the month after the last training date.
    """
    return pd.date_range(train.index[-1] + pd.offsets.MonthBegin(1), periods=horizon, freq="MS")


def _alpha():
    """Return the significance level for prediction intervals.
    
    Returns
    -------
    float
        1 - INTERVAL_LEVEL (e.g. 0.05 for 95% intervals).
    """
    return 1 - config.INTERVAL_LEVEL


def _select_by_aic(rows):
    """Pick a candidate model by AIC with a parsimony rule.
    
    Among converged candidates within AIC_TOLERANCE of the lowest AIC, the one
    with the fewest parameters wins; ties go to the lower AIC.
    
    Parameters
    ----------
    rows : list of dict
        Each dict has "aic", "n_params", "converged" keys plus extra info.
    
    Returns
    -------
    tuple of (int, pandas.DataFrame)
        (chosen_row_index, sorted_candidates_table).
    """
    table = pd.DataFrame(rows)                         # Convert list of dicts to DataFrame
    usable = table[table["converged"] & table["aic"].notna()]  # Only converged, non-NaN AIC
    if usable.empty:
        raise RuntimeError("No candidate model converged")
    best_aic = usable["aic"].min()                     # Lowest AIC
    table["delta_aic"] = table["aic"] - best_aic       # AIC difference from best
    supported = usable[usable["aic"] <= best_aic + config.AIC_TOLERANCE]  # Within tolerance
    chosen = supported.sort_values(["n_params", "aic"]).index[0]  # Fewest params, then lowest AIC
    table["selected"] = table.index == chosen          # Mark the chosen row
    return chosen, table.sort_values("aic").reset_index(drop=True)  # Return chosen index and sorted table


# --- ARIMA -------------------------------------------------------------------

def fit_arima(train, horizon=config.HORIZON):
    """Fit ARIMA(p, 1, q) with drift; p, q and seasonal part chosen by AIC.
    
    The ARIMA class uses trend="t" with d=1, which is a constant drift (fixed
    average change per month). This differs from SARIMAX's trend="t" which
    would put a trend on monthly changes (causing accelerating forecasts).
    
    Parameters
    ----------
    train : pandas.Series
        Monthly CPI training data indexed by date.
    horizon : int
        Number of months to forecast.
    
    Returns
    -------
    ForecastResult
        ARIMA forecast with prediction interval and parameters.
    """
    rows, fits = [], []
    for p, q, seasonal in itertools.product(          # Try all combinations of p, q, seasonal
        config.ARIMA_P_VALUES, config.ARIMA_Q_VALUES, config.ARIMA_SEASONAL_CANDIDATES
    ):
        order = (p, config.ARIMA_D, q)                 # ARIMA(p, d, q) order
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                fitted = ARIMA(train, order=order, seasonal_order=seasonal, trend="t").fit()
            except (ValueError, np.linalg.LinAlgError):  # Model failed to fit
                fitted = None
        converged = fitted is not None and not any(  # Check for convergence warnings
            issubclass(w.category, ConvergenceWarning) for w in caught
        )
        fits.append(fitted)
        rows.append({
            "order": order,
            "seasonal_order": seasonal,
            "aic": fitted.aic if fitted is not None else np.nan,
            "n_params": len(fitted.params) if fitted is not None else np.nan,
            "converged": converged,
        })

    chosen, candidates = _select_by_aic(rows)          # Pick best by AIC with parsimony
    fitted = fits[chosen]
    order, seasonal = rows[chosen]["order"], rows[chosen]["seasonal_order"]

    index = _future_index(train, horizon)              # Forecast dates
    pred = fitted.get_forecast(horizon)                # Generate forecast
    ci = pred.conf_int(alpha=_alpha())                 # Prediction interval
    return ForecastResult(
        model="ARIMA",
        forecast=pd.Series(pred.predicted_mean.values, index=index),
        lower=pd.Series(ci.iloc[:, 0].values, index=index),
        upper=pd.Series(ci.iloc[:, 1].values, index=index),
        params={
            "order": order,
            "seasonal_order": seasonal,
            "aic": fitted.aic,
            "drift_per_month": float(fitted.params.iloc[0]),  # Constant drift = average monthly change
        },
        candidates=candidates,
        fitted=fitted,
    )


# --- Linear Regression -------------------------------------------------------

def fit_linear_regression(train, horizon=config.HORIZON):
    """Fit CPI regressed on a time index (overall trend) using OLS.
    
    Parameters
    ----------
    train : pandas.Series
        Monthly CPI training data indexed by date.
    horizon : int
        Number of months to forecast.
    
    Returns
    -------
    ForecastResult
        Linear regression forecast with prediction interval and parameters.
    """
    t = np.arange(1, len(train) + 1)                   # Time index: 1, 2, ..., n
    fitted = sm.OLS(train.values, sm.add_constant(t)).fit()  # OLS regression with intercept

    t_future = np.arange(len(train) + 1, len(train) + horizon + 1)  # Future time index
    frame = fitted.get_prediction(sm.add_constant(t_future)).summary_frame(alpha=_alpha())  # Predictions + intervals

    index = _future_index(train, horizon)
    intercept, slope = fitted.params
    return ForecastResult(
        model="Linear Regression",
        forecast=pd.Series(frame["mean"].values, index=index),
        lower=pd.Series(frame["obs_ci_lower"].values, index=index),  # Prediction interval for new observation
        upper=pd.Series(frame["obs_ci_upper"].values, index=index),
        params={"intercept": intercept, "slope_per_month": slope, "r_squared": fitted.rsquared},
        fitted=fitted,
    )


# --- Moving Average ----------------------------------------------------------

def _ma_errors(series, k, horizon):
    """Compute past errors of a k-month moving average forecast at each horizon step.
    
    Used to build empirical prediction intervals (moving average has no
    statistical model for intervals).
    
    Parameters
    ----------
    series : pandas.Series
        Full time series.
    k : int
        Moving average window size.
    horizon : int
        Forecast horizon.
    
    Returns
    -------
    dict of int -> list of float
        Errors at each step ahead (1 to horizon).
    """
    values = series.values
    errors = {h: [] for h in range(1, horizon + 1)}
    for origin in range(k - 1, len(values) - 1):       # Every possible origin
        level = values[origin - k + 1: origin + 1].mean()  # Mean of last k values
        for h in range(1, horizon + 1):
            if origin + h < len(values):
                errors[h].append(values[origin + h] - level)  # Forecast error
    return errors


def fit_moving_average(train, horizon=config.HORIZON):
    """Fit a flat moving average forecast: mean of the last k months.
    
    k is chosen by lowest RMSE on the last VALIDATION_MONTHS of train
    (validation window). Prediction intervals come from the empirical
    distribution of past errors at each horizon step.
    
    Parameters
    ----------
    train : pandas.Series
        Monthly CPI training data indexed by date.
    horizon : int
        Number of months to forecast.
    
    Returns
    -------
    ForecastResult
        Moving average forecast with empirical prediction intervals.
    """
    fit_part = train.iloc[: -config.VALIDATION_MONTHS]   # Training portion (exclude validation window)
    validation = train.iloc[-config.VALIDATION_MONTHS:]  # Validation portion (last 12 months)

    rows = []
    for k in config.MA_WINDOWS:                          # Try each window size
        level = fit_part.iloc[-k:].mean()                # Mean of last k months of training
        rmse = np.sqrt(np.mean((validation.values - level) ** 2))  # RMSE on validation
        rows.append({"k": k, "validation_rmse": rmse})
    candidates = pd.DataFrame(rows).sort_values("validation_rmse").reset_index(drop=True)
    k = int(candidates.loc[0, "k"])                      # Best window size

    level = train.iloc[-k:].mean()                       # Final level: mean of last k months of all training
    index = _future_index(train, horizon)
    forecast = pd.Series(level, index=index)             # Flat forecast

    errors = _ma_errors(train, k, horizon)               # Past errors for intervals
    lo_q, hi_q = _alpha() / 2, 1 - _alpha() / 2          # Quantiles for 95% interval
    lower = [level + np.quantile(errors[h], lo_q) for h in range(1, horizon + 1)]
    upper = [level + np.quantile(errors[h], hi_q) for h in range(1, horizon + 1)]

    return ForecastResult(
        model="Moving Average",
        forecast=forecast,
        lower=pd.Series(lower, index=index),
        upper=pd.Series(upper, index=index),
        params={"k": k, "level": level},
        candidates=candidates,
    )


# --- ETS (extra, not in the proposal) ---------------------------------------

def fit_ets(train, horizon=config.HORIZON):
    """Fit Exponential Smoothing with additive error and trend (Holt's method).
    
    With or without damped trend, chosen by AIC. No seasonal component since
    exploratory checks found seasonality weak.
    
    Parameters
    ----------
    train : pandas.Series
        Monthly CPI training data indexed by date.
    horizon : int
        Number of months to forecast.
    
    Returns
    -------
    ForecastResult
        ETS forecast with prediction interval and parameters.
    """
    rows, fits = [], []
    for damped in config.ETS_DAMPED_OPTIONS:             # Try damped and non-damped trend
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fitted = ETSModel(train, error="add", trend="add", damped_trend=damped).fit(disp=False)
        fits.append(fitted)
        rows.append({
            "damped_trend": damped,
            "aic": fitted.aic,
            "n_params": len(fitted.params),
            "converged": not any(issubclass(w.category, ConvergenceWarning) for w in caught),
        })

    chosen, candidates = _select_by_aic(rows)            # Pick best by AIC with parsimony
    fitted, damped = fits[chosen], rows[chosen]["damped_trend"]

    index = _future_index(train, horizon)
    frame = fitted.get_prediction(start=index[0], end=index[-1]).summary_frame(alpha=_alpha())
    params = {"damped_trend": damped, "aic": fitted.aic}
    params.update({name: float(fitted.params[i]) for i, name in enumerate(fitted.param_names)
                   if name in ("smoothing_level", "smoothing_trend", "damping_trend")})
    return ForecastResult(
        model="ETS",
        forecast=pd.Series(frame["mean"].values, index=index),
        lower=pd.Series(frame["pi_lower"].values, index=index),
        upper=pd.Series(frame["pi_upper"].values, index=index),
        params=params,
        candidates=candidates,
        fitted=fitted,
    )


# Dictionary mapping model names to their fit functions.
MODELS = {
    "ARIMA": fit_arima,
    "Linear Regression": fit_linear_regression,
    "Moving Average": fit_moving_average,
    "ETS": fit_ets,
}


def fit_all(train, horizon=config.HORIZON, models=None):
    """Fit every model (or the named subset) from the same origin.
    
    Parameters
    ----------
    train : pandas.Series
        Monthly CPI training data indexed by date.
    horizon : int
        Number of months to forecast.
    models : list of str or None
        Model names to fit. None means all models.
    
    Returns
    -------
    dict of str -> ForecastResult
        Model name to forecast result mapping.
    """
    names = models or list(MODELS)
    return {name: MODELS[name](train, horizon) for name in names}
