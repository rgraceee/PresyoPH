"""Scoring and model selection for the CPI forecasts."""

import numpy as np
import pandas as pd

from modeling import config
from modeling.derive import derive_all, derive_intervals
from modeling.models import fit_all


def mae(actual, forecast):
    return float(np.mean(np.abs(actual - forecast)))


def rmse(actual, forecast):
    return float(np.sqrt(np.mean((actual - forecast) ** 2)))


def mape(actual, forecast):
    if (actual == 0).any():
        return np.nan
    return float(np.mean(np.abs((actual - forecast) / actual)) * 100)


METRIC_FUNCTIONS = {"MAE": mae, "RMSE": rmse, "MAPE": mape}


def score(actual, forecast):
    actual, forecast = actual.align(forecast, join="inner")
    out = {name: fn(actual, forecast) for name, fn in METRIC_FUNCTIONS.items()}
    out["n_months"] = len(actual)
    return out


def forecast_from(cpi, origin, horizon=config.HORIZON, models=None):
    history = cpi[:origin]
    results = fit_all(history, horizon=horizon, models=models)

    frames = []
    for name, r in results.items():
        derived = derive_all(history, r.forecast)
        bounds = derive_intervals(history, r.lower, r.upper)
        bounds["cpi_lower"], bounds["cpi_upper"] = r.lower, r.upper
        for variable in config.VARIABLES:
            frames.append(pd.DataFrame({
                "date": r.forecast.index,
                "variable": variable,
                "forecast": derived[variable].values,
                "lower": bounds[f"{variable}_lower"].values,
                "upper": bounds[f"{variable}_upper"].values,
                "model": name,
                "step": range(1, len(r.forecast) + 1),
            }))

    predictions = pd.concat(frames, ignore_index=True)
    predictions.insert(0, "origin", pd.Timestamp(origin))
    return results, predictions


def attach_actuals(predictions, actuals):
    lookup = pd.concat(
        {var: series for var, series in actuals.items()}, names=["variable", "date"]
    ).rename("actual")
    out = predictions.merge(lookup.reset_index(), on=["variable", "date"], how="left")
    out["error"] = out["actual"] - out["forecast"]
    return out


def metrics_table(predictions, start=None, end=None):
    rows = predictions.dropna(subset=["actual"])
    if start is not None:
        rows = rows[rows["date"] >= pd.Timestamp(start)]
    if end is not None:
        rows = rows[rows["date"] <= pd.Timestamp(end)]

    records = []
    for (model, variable), group in rows.groupby(["model", "variable"], sort=False):
        series = group.set_index("date")
        records.append({"model": model, "variable": variable,
                        **score(series["actual"], series["forecast"])})
    return pd.DataFrame(records)


def eligible_models():
    models = list(config.PROPOSAL_MODELS)
    if config.ETS_ELIGIBLE_FOR_SELECTION:
        models += config.EXTRA_MODELS
    return models


def select_model(metrics, variable=config.SELECTION_VARIABLE, models=None):
    """2-of-3-metrics rule; else lowest RMSE."""
    models = models or eligible_models()
    table = metrics[(metrics["variable"] == variable) & (metrics["model"].isin(models))]
    table = table.set_index("model")[config.METRICS]

    best_per_metric = {m: table[m].idxmin() for m in config.METRICS}
    wins = pd.Series(0, index=table.index)
    for model in best_per_metric.values():
        wins[model] += 1

    leaders = wins[wins >= 2]
    if len(leaders) == 1:
        winner = leaders.index[0]
        won_on = [m for m, model in best_per_metric.items() if model == winner]
        explanation = f"{winner} has the lowest {', '.join(won_on)} ({len(won_on)} of 3 metrics)."
    else:
        winner = table[config.TIEBREAK_METRIC].idxmin()
        explanation = (f"No model is best on at least 2 of 3 metrics; {winner} has the "
                       f"lowest {config.TIEBREAK_METRIC}.")
    return winner, explanation, wins


def rolling_origin(cpi, actuals, origins=config.ROLLING_ORIGINS, horizon=config.ROLLING_HORIZON, models=None):
    all_predictions, all_metrics = [], []
    for origin in origins:
        _, predictions = forecast_from(cpi, origin, horizon=horizon, models=models)
        predictions = attach_actuals(predictions, actuals)
        fold_metrics = metrics_table(predictions)
        fold_metrics.insert(0, "origin", pd.Timestamp(origin))
        all_predictions.append(predictions)
        all_metrics.append(fold_metrics)
    return pd.concat(all_predictions, ignore_index=True), pd.concat(all_metrics, ignore_index=True)


def average_over_folds(fold_metrics):
    return (fold_metrics.groupby(["model", "variable"], sort=False)[config.METRICS]
            .mean().reset_index())


def select_final_model(main_predictions, rolling_predictions):
    if config.SELECTION_BASIS == "pooled":
        basis = pd.concat([rolling_predictions, main_predictions], ignore_index=True)
    elif config.SELECTION_BASIS == "main_test":
        basis = main_predictions
    else:
        raise ValueError(f"Unknown SELECTION_BASIS: {config.SELECTION_BASIS!r}")
    metrics = metrics_table(basis)
    winner, explanation, wins = select_model(metrics)
    return winner, explanation, wins, metrics


def error_by_step(predictions, variable="cpi"):
    rows = predictions[(predictions["variable"] == variable)].dropna(subset=["actual"])
    return (rows.assign(abs_error=rows["error"].abs())
            .pivot_table(index="step", columns="model", values="abs_error", aggfunc="mean"))
