"""
================================================================================
FILE: modeling/run_pipeline.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
This file runs the full CPI forecasting pipeline and saves its outputs (task 5).

It:
  1. Loads CPI, inflation, and purchasing power series from the database
  2. Evaluates every model on the main test set (Sep 2025 - Aug 2026)
  3. Evaluates every model on rolling-origin folds (5 origins)
  4. Selects the final model using the 2-of-3-metrics rule on pooled results
  5. Refits all models on all data and produces 12-month forecasts
  6. Writes results to datasets/outputs/:
     - forecasts.csv
     - test_predictions.csv
     - metrics.csv
     - error_by_step.csv
     - model_info.json

Run with: python -m modeling.run_pipeline

Re-run whenever the data is refreshed.

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- backend/sources.py: Imports series() to load data from the database.
- modeling/config.py: Imports config for all evaluation settings.
- modeling/evaluation.py: Imports as ev, calls forecast_from(), attach_actuals(),
  metrics_table(), select_final_model(), error_by_step(), average_over_folds(),
  eligible_models().
- datasets/outputs/: Writes CSV files and model_info.json here.
- backend/data.py: Reads these output files when the dashboard needs forecasts.

================================================================================
"""

"""Run the full forecasting pipeline and save its outputs (task 5).

    .venv/Scripts/python -m modeling.run_pipeline

Loads CPI and the published inflation and purchasing power series, evaluates
every model (main test and rolling origin), selects the final model, refits
all models on the full data, and writes the results to datasets/outputs/.
Re-run it whenever the data is refreshed. The file layout is described in
datasets/outputs/README.md.
"""

import json                                           # json: read/write model_info.json
from datetime import datetime                         # datetime: timestamp for when pipeline ran
from pathlib import Path                              # Path: file system paths

import pandas as pd                                   # pandas: DataFrame operations

from backend.sources import series                    # Load time series from database
from modeling import config                           # config: evaluation settings
from modeling import evaluation as ev                 # evaluation: scoring and selection

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "datasets" / "outputs"


def _json_safe(value):
    """Convert a value to a JSON-serializable form.
    
    Parameters
    ----------
    value : any
        Value to convert.
    
    Returns
    -------
    any
        JSON-safe version of the value.
    """
    if isinstance(value, tuple):                       # Tuples aren't JSON-serializable
        return list(value)
    if hasattr(value, "item"):                         # NumPy scalars
        return value.item()
    return value


def _metrics_rows(metrics, evaluation, period):
    """Add evaluation and period columns to a metrics DataFrame.
    
    Parameters
    ----------
    metrics : pandas.DataFrame
        Metrics output from evaluation.metrics_table().
    evaluation : str
        Evaluation type name.
    period : str
        Period label.
    
    Returns
    -------
    pandas.DataFrame
        Metrics with evaluation and period columns added at the front.
    """
    out = metrics.rename(columns={"MAE": "mae", "RMSE": "rmse", "MAPE": "mape"})  # Lowercase column names
    out.insert(0, "period", period)
    out.insert(0, "evaluation", evaluation)
    return out


def run():
    """Execute the full forecasting pipeline and save all outputs."""
    # Load actual data series from the database
    actuals = {name: series(name) for name in config.VARIABLES}
    cpi = actuals["cpi"]

    # --- Evaluation: main test and rolling origin ---
    _, main = ev.forecast_from(cpi, config.TRAIN_END)    # Forecast from main test origin
    main = ev.attach_actuals(main, actuals)              # Add actual values
    rolling, fold_metrics = ev.rolling_origin(cpi, actuals)  # Rolling-origin evaluation

    # Select the final model using the selection rule
    final_model, explanation, wins, _ = ev.select_final_model(main, rolling)

    # --- Final forecasts: refit all models on all data ---
    final_results, final = ev.forecast_from(cpi, config.DATA_END)  # Forecast from end of data
    final["is_selected"] = final["model"] == final_model  # Mark the selected model

    # --- forecasts.csv ---
    forecasts = final[["origin", "model", "variable", "date", "step", "forecast", "lower", "upper", "is_selected"]]

    # --- test_predictions.csv ---
    predictions = pd.concat([
        main.assign(evaluation="main_test"),
        rolling.assign(evaluation="rolling_origin"),
    ], ignore_index=True)
    predictions = predictions[["evaluation", "origin", "model", "variable", "date", "step",
                               "forecast", "lower", "upper", "actual", "error"]]

    # --- metrics.csv ---
    pooled = pd.concat([rolling, main], ignore_index=True)  # Combine all origins
    full_test = list(config.TEST_SUBPERIODS)[0]           # First sub-period label
    metric_frames = [_metrics_rows(ev.metrics_table(pooled), "pooled", "all six origins")]
    for label, (start, end) in config.TEST_SUBPERIODS.items():
        metric_frames.append(_metrics_rows(ev.metrics_table(main, start, end), "main_test", label))
    for origin, group in fold_metrics.groupby("origin"):
        metric_frames.append(_metrics_rows(group.drop(columns="origin"), "rolling_fold",
                                           f"origin {origin:%Y-%m}"))
    metric_frames.append(_metrics_rows(ev.average_over_folds(fold_metrics), "rolling_average",
                                       "mean of five folds"))
    metrics = pd.concat(metric_frames, ignore_index=True)
    metrics["is_selected_model"] = metrics["model"] == final_model
    if config.SELECTION_BASIS == "pooled":
        metrics["used_for_selection"] = metrics["evaluation"] == "pooled"
    else:
        metrics["used_for_selection"] = (metrics["evaluation"] == "main_test") & (metrics["period"] == full_test)

    # --- error_by_step.csv (pooled over all six origins) ---
    steps = []
    for variable in config.VARIABLES:
        table = ev.error_by_step(pooled, variable).reset_index().melt(
            id_vars="step", var_name="model", value_name="mae")
        table.insert(0, "variable", variable)
        steps.append(table)
    error_by_step = pd.concat(steps, ignore_index=True)

    # --- model_info.json ---
    info = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "final_model": final_model,
        "selection": {
            "variable": config.SELECTION_VARIABLE,
            "basis": config.SELECTION_BASIS,
            "rule": "Lowest error on at least 2 of MAE, RMSE, MAPE; otherwise lowest RMSE.",
            "explanation": explanation,
            "metric_wins": {k: int(v) for k, v in wins.items()},
            "eligible_models": ev.eligible_models(),
        },
        "data": {
            "series": f"{config.TARGET_AREA}, {config.TARGET_ITEM}",
            "start": f"{config.DATA_START:%Y-%m}",
            "end": f"{config.DATA_END:%Y-%m}",
            "train_end": f"{config.TRAIN_END:%Y-%m}",
            "test": f"{config.TEST_START:%Y-%m} to {config.TEST_END:%Y-%m}",
            "rolling_origins": [f"{o:%Y-%m}" for o in config.ROLLING_ORIGINS],
        },
        "forecast": {
            "origin": f"{config.DATA_END:%Y-%m}",
            "horizon_months": config.HORIZON,
            "dashboard_horizons": config.DASHBOARD_HORIZONS,
            "interval_level": config.INTERVAL_LEVEL,
        },
        "final_model_params": {name: {k: _json_safe(v) for k, v in r.params.items()}
                               for name, r in final_results.items()},
        "notes": [
            "Only CPI is modeled. Inflation and purchasing power are derived from the CPI forecast.",
            "ETS is not in the proposal and is reported for comparison only.",
            "The selection basis was changed from the main test to the pooled six origins after the results were seen.",
            "Forecasts rely only on historical CPI and do not account for external factors.",
        ],
    }

    # Write all output files
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "forecasts.csv": forecasts,
        "test_predictions.csv": predictions,
        "metrics.csv": metrics,
        "error_by_step.csv": error_by_step,
    }
    for name, frame in files.items():
        frame.to_csv(OUTPUT_DIR / name, index=False, float_format="%.6f", date_format="%Y-%m-%d")
    (OUTPUT_DIR / "model_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")

    print(f"Final model: {final_model}. {explanation}")
    for name, frame in files.items():
        print(f"  wrote {name:<22} {len(frame):>5} rows")
    print("  wrote model_info.json")


if __name__ == "__main__":
    run()
