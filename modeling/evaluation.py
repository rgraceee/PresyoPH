"""
================================================================================
FILE: modeling/evaluation.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
This file handles scoring and model selection for the CPI forecasts (task 4).

It provides:
  - Metric functions: MAE, RMSE, MAPE
  - score(): compute all three metrics for actual vs. forecast
  - forecast_from(): fit all models from a given origin and produce forecasts
  - attach_actuals(): add actual values to predictions for error calculation
  - metrics_table(): score models over a period
  - select_model(): apply the 2-of-3-metrics selection rule
  - rolling_origin(): evaluate models across multiple origins
  - select_final_model(): choose the final model using the selection basis
  - error_by_step(): MAE at each forecast step ahead

Each model forecasts CPI from a given origin. Inflation and purchasing power
are derived from that CPI forecast (option B) and all three are scored against
PSA's published series.

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- modeling/config.py: Imports config for HORIZON, VARIABLES, METRICS,
  SELECTION_VARIABLE, SELECTION_BASIS, TIEBREAK_METRIC, ROLLING_ORIGINS,
  ROLLING_HORIZON, PROPOSAL_MODELS, EXTRA_MODELS, ETS_ELIGIBLE_FOR_SELECTION.
- modeling/derive.py: Imports derive_all(), derive_intervals().
- modeling/models.py: Imports fit_all().
- modeling/run_pipeline.py: Imports evaluation as ev, calls forecast_from(),
  attach_actuals(), metrics_table(), select_final_model(), error_by_step(),
  average_over_folds(), eligible_models().

================================================================================
"""

"""Scoring and model selection for the CPI forecasts (task 4).

Each model forecasts CPI from a given origin. Inflation and purchasing power
are derived from that CPI forecast (option B) and all three are scored against
PSA's published series. The final model is chosen on CPI with the rule in
modeling/config.py.
"""

import numpy as np                                    # numpy: numerical operations
import pandas as pd                                   # pandas: DataFrame operations

from modeling import config                           # config: evaluation settings
from modeling.derive import derive_all, derive_intervals  # derive: CPI -> inflation, purchasing power
from modeling.models import fit_all                   # models: fit all forecasting models


# --- Metrics -----------------------------------------------------------------
# Error measure functions used to score forecasts against actual values.

def mae(actual, forecast):
    """Mean Absolute Error: average of absolute differences.
    
    Parameters
    ----------
    actual : array-like
        Actual values.
    forecast : array-like
        Forecasted values.
    
    Returns
    -------
    float
        MAE value.
    """
    return float(np.mean(np.abs(actual - forecast)))   # Mean of |actual - forecast|


def rmse(actual, forecast):
    """Root Mean Squared Error: square root of average squared differences.
    
    Penalises large errors more than MAE.
    
    Parameters
    ----------
    actual : array-like
        Actual values.
    forecast : array-like
        Forecasted values.
    
    Returns
    -------
    float
        RMSE value.
    """
    return float(np.sqrt(np.mean((actual - forecast) ** 2)))  # sqrt(mean((actual - forecast)^2))


def mape(actual, forecast):
    """Mean Absolute Percentage Error: average error as percent of actual.
    
    Undefined (NaN) if any actual value is zero. Unreliable when inflation
    is near zero (small miss = large percentage error).
    
    Parameters
    ----------
    actual : array-like
        Actual values.
    forecast : array-like
        Forecasted values.
    
    Returns
    -------
    float or nan
        MAPE value in percent, or NaN if any actual is zero.
    """
    if (actual == 0).any():                            # Can't divide by zero
        return np.nan
    return float(np.mean(np.abs((actual - forecast) / actual)) * 100)  # Mean of |(actual-forecast)/actual| * 100


METRIC_FUNCTIONS = {"MAE": mae, "RMSE": rmse, "MAPE": mape}  # Map metric name to function


def score(actual, forecast):
    """Compute MAE, RMSE, and MAPE over the months the two series share.
    
    Parameters
    ----------
    actual : pandas.Series
        Actual values indexed by date.
    forecast : pandas.Series
        Forecast values indexed by date.
    
    Returns
    -------
    dict
        Keys: "MAE", "RMSE", "MAPE", "n_months".
    """
    actual, forecast = actual.align(forecast, join="inner")  # Keep only dates present in both
    out = {name: fn(actual, forecast) for name, fn in METRIC_FUNCTIONS.items()}  # Compute all three metrics
    out["n_months"] = len(actual)                        # Number of overlapping months
    return out


# --- Forecasting from an origin ----------------------------------------------

def forecast_from(cpi, origin, horizon=config.HORIZON, models=None):
    """Fit every model on CPI up to `origin` and forecast `horizon` months.
    
    Parameters
    ----------
    cpi : pandas.Series
        Full CPI history indexed by date.
    origin : pd.Timestamp
        Last training month (forecast starts the month after).
    horizon : int
        Number of months to forecast (default from config.HORIZON = 12).
    models : list of str or None
        Model names to fit. None means all models.
    
    Returns
    -------
    tuple of (dict, pandas.DataFrame)
        (results, predictions):
        - results: dict of model_name -> ForecastResult (from modeling.models)
        - predictions: long DataFrame with one row per model, variable, month
    """
    history = cpi[:origin]                               # Training data: everything up to origin
    results = fit_all(history, horizon=horizon, models=models)  # Fit all models from modeling/models.py

    frames = []
    for name, r in results.items():                      # For each model's forecast result
        derived = derive_all(history, r.forecast)        # Derive inflation and purchasing power from CPI forecast
        bounds = derive_intervals(history, r.lower, r.upper)  # Derive prediction intervals
        bounds["cpi_lower"], bounds["cpi_upper"] = r.lower, r.upper  # Add CPI bounds
        for variable in config.VARIABLES:                # One row set per variable (cpi, inflation, purchasing_power)
            frames.append(pd.DataFrame({
                "date": r.forecast.index,                # Forecast dates
                "variable": variable,                    # Which variable
                "forecast": derived[variable].values,    # Point forecast
                "lower": bounds[f"{variable}_lower"].values,  # Lower bound
                "upper": bounds[f"{variable}_upper"].values,  # Upper bound
                "model": name,                           # Model name
                "step": range(1, len(r.forecast) + 1),   # Months ahead (1, 2, ..., horizon)
            }))

    predictions = pd.concat(frames, ignore_index=True)   # Combine all rows
    predictions.insert(0, "origin", pd.Timestamp(origin))  # Add origin column at the front
    return results, predictions


def attach_actuals(predictions, actuals):
    """Add the published actual value for each prediction row.
    
    Parameters
    ----------
    predictions : pandas.DataFrame
        Output of forecast_from() with columns: variable, date, forecast, etc.
    actuals : dict of str -> pandas.Series
        Maps variable name to its published monthly series.
    
    Returns
    -------
    pandas.DataFrame
        Predictions with an added "actual" column and "error" column
        (error = actual - forecast).
    """
    lookup = pd.concat(
        {var: series for var, series in actuals.items()}, names=["variable", "date"]
    ).rename("actual")                                   # Stack all actual series with multi-index
    out = predictions.merge(lookup.reset_index(), on=["variable", "date"], how="left")  # Join actuals
    out["error"] = out["actual"] - out["forecast"]       # Error = actual - forecast
    return out


def metrics_table(predictions, start=None, end=None):
    """Score every model and variable over [start, end] (inclusive).
    
    Parameters
    ----------
    predictions : pandas.DataFrame
        Output of attach_actuals() with actual and forecast columns.
    start : str or pd.Timestamp or None
        Start date filter.
    end : str or pd.Timestamp or None
        End date filter.
    
    Returns
    -------
    pandas.DataFrame
        Columns: model, variable, mae, rmse, mape, n_months.
    """
    rows = predictions.dropna(subset=["actual"])         # Remove rows without actual values
    if start is not None:
        rows = rows[rows["date"] >= pd.Timestamp(start)]
    if end is not None:
        rows = rows[rows["date"] <= pd.Timestamp(end)]

    records = []
    for (model, variable), group in rows.groupby(["model", "variable"], sort=False):
        series = group.set_index("date")                  # Index by date for alignment
        records.append({"model": model, "variable": variable,
                        **score(series["actual"], series["forecast"])})  # Compute metrics
    return pd.DataFrame(records)


# --- Model selection ---------------------------------------------------------

def eligible_models():
    """Return the list of models eligible for selection.
    
    Proposal models are always eligible. ETS is only eligible if
    config.ETS_ELIGIBLE_FOR_SELECTION is True.
    
    Returns
    -------
    list of str
        Model names.
    """
    models = list(config.PROPOSAL_MODELS)
    if config.ETS_ELIGIBLE_FOR_SELECTION:
        models += config.EXTRA_MODELS
    return models


def select_model(metrics, variable=config.SELECTION_VARIABLE, models=None):
    """Apply the selection rule to one variable's metrics.
    
    Rule:
      1. A model with the lowest error on at least 2 of the 3 metrics wins.
      2. Otherwise, the model with the lowest RMSE wins.
    
    Parameters
    ----------
    metrics : pandas.DataFrame
        Model metrics output from metrics_table().
    variable : str
        Variable to select on (default "cpi").
    models : list of str or None
        Models to consider. None means eligible models.
    
    Returns
    -------
    tuple of (str, str, pandas.Series)
        (winner, explanation, wins):
        - winner: name of the selected model
        - explanation: human-readable explanation of why
        - wins: count of metrics each model won
    """
    models = models or eligible_models()
    table = metrics[(metrics["variable"] == variable) & (metrics["model"].isin(models))]
    table = table.set_index("model")[config.METRICS]     # Just the metric columns

    best_per_metric = {m: table[m].idxmin() for m in config.METRICS}  # Best model for each metric
    wins = pd.Series(0, index=table.index)               # Initialize win counts
    for model in best_per_metric.values():               # Count wins for each model
        wins[model] += 1

    leaders = wins[wins >= 2]                            # Models that won at least 2 metrics
    if len(leaders) == 1:                                # Exactly one model won 2+ metrics
        winner = leaders.index[0]
        won_on = [m for m, model in best_per_metric.items() if model == winner]
        explanation = f"{winner} has the lowest {', '.join(won_on)} ({len(won_on)} of 3 metrics)."
    else:                                                # No clear winner, use tiebreaker
        winner = table[config.TIEBREAK_METRIC].idxmin()  # Lowest RMSE
        explanation = (f"No model is best on at least 2 of 3 metrics; {winner} has the "
                       f"lowest {config.TIEBREAK_METRIC}.")
    return winner, explanation, wins


# --- Rolling-origin evaluation -----------------------------------------------

def rolling_origin(cpi, actuals, origins=config.ROLLING_ORIGINS, horizon=config.ROLLING_HORIZON, models=None):
    """Run rolling-origin evaluation: forecast from each origin and score each fold.
    
    Parameters
    ----------
    cpi : pandas.Series
        Full CPI history.
    actuals : dict of str -> pandas.Series
        Published actual series for each variable.
    origins : pandas.DatetimeIndex
        List of origin dates (last training month for each fold).
    horizon : int
        Forecast horizon in months.
    models : list of str or None
        Models to evaluate.
    
    Returns
    -------
    tuple of (pandas.DataFrame, pandas.DataFrame)
        (all_predictions, all_metrics): combined predictions and metrics
        from all origins.
    """
    all_predictions, all_metrics = [], []
    for origin in origins:
        _, predictions = forecast_from(cpi, origin, horizon=horizon, models=models)
        predictions = attach_actuals(predictions, actuals)  # Add actual values
        fold_metrics = metrics_table(predictions)          # Score this fold
        fold_metrics.insert(0, "origin", pd.Timestamp(origin))  # Add origin column
        all_predictions.append(predictions)
        all_metrics.append(fold_metrics)
    return pd.concat(all_predictions, ignore_index=True), pd.concat(all_metrics, ignore_index=True)


def average_over_folds(fold_metrics):
    """Compute the mean of each metric across folds, per model and variable.
    
    Parameters
    ----------
    fold_metrics : pandas.DataFrame
        Output of rolling_origin() with columns model, variable, mae, rmse, mape.
    
    Returns
    -------
    pandas.DataFrame
        Mean metrics per model and variable.
    """
    return (fold_metrics.groupby(["model", "variable"], sort=False)[config.METRICS]
            .mean().reset_index())


def select_final_model(main_predictions, rolling_predictions):
    """Apply the selection rule on the basis set in config.SELECTION_BASIS.
    
    "pooled" scores all six origins together (main test plus rolling folds);
    "main_test" scores the main 12-month test only.
    
    Parameters
    ----------
    main_predictions : pandas.DataFrame
        Predictions from the main test origin.
    rolling_predictions : pandas.DataFrame
        Predictions from rolling-origin folds.
    
    Returns
    -------
    tuple of (str, str, pandas.Series, pandas.DataFrame)
        (winner, explanation, wins, metrics_used).
    """
    if config.SELECTION_BASIS == "pooled":
        basis = pd.concat([rolling_predictions, main_predictions], ignore_index=True)  # Combine all
    elif config.SELECTION_BASIS == "main_test":
        basis = main_predictions                           # Main test only
    else:
        raise ValueError(f"Unknown SELECTION_BASIS: {config.SELECTION_BASIS!r}")
    metrics = metrics_table(basis)                         # Score the basis
    winner, explanation, wins = select_model(metrics)      # Apply selection rule
    return winner, explanation, wins, metrics


def error_by_step(predictions, variable="cpi"):
    """Compute mean absolute error at each step ahead (1-12 months), per model.
    
    Parameters
    ----------
    predictions : pandas.DataFrame
        Output of attach_actuals() with error column.
    variable : str
        Variable to analyze (default "cpi").
    
    Returns
    -------
    pandas.DataFrame
        Pivot table: index = step, columns = model, values = mean absolute error.
    """
    rows = predictions[(predictions["variable"] == variable)].dropna(subset=["actual"])
    return (rows.assign(abs_error=rows["error"].abs())     # Absolute error
            .pivot_table(index="step", columns="model", values="abs_error", aggfunc="mean"))
