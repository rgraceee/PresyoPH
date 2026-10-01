"""Where the backend gets its data. The only module to change when Member 1's
database is ready.

Historical data currently comes from the temporary loader, which reads the
raw PSA exports. Forecasting outputs come from datasets/outputs/, written by
modeling/run_pipeline.py. To switch to the database, reimplement these
functions with the same names and return columns; nothing in backend/data.py
needs to change.

All functions are cached. Callers must not modify the returned frames.
"""

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

from modeling import temp_loader

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "datasets" / "outputs"


def price_table(indicator):
    """Columns: area, area_level, item, date, value."""
    return temp_loader.load_price_table(indicator)


def fies_table():
    """Columns: area, area_level, decile, income, expenditure, savings."""
    return temp_loader.load_fies()


def regions():
    """The 18 region names, in PSA order."""
    return list(temp_loader.REGIONS)


def _read_output(name, dates=()):
    path = OUTPUT_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python -m modeling.run_pipeline` to create the forecasting outputs."
        )
    return pd.read_csv(path, parse_dates=list(dates))


@lru_cache(maxsize=None)
def forecasts_table():
    """Columns: origin, model, variable, date, step, forecast, lower, upper, is_selected."""
    return _read_output("forecasts.csv", dates=("origin", "date"))


@lru_cache(maxsize=None)
def test_predictions_table():
    """Columns: evaluation, origin, model, variable, date, step, forecast, lower, upper, actual, error."""
    return _read_output("test_predictions.csv", dates=("origin", "date"))


@lru_cache(maxsize=None)
def metrics_table():
    """Columns: evaluation, period, model, variable, mae, rmse, mape, n_months,
    is_selected_model, used_for_selection."""
    return _read_output("metrics.csv")


@lru_cache(maxsize=None)
def error_by_step_table():
    """Columns: variable, model, step, mae."""
    return _read_output("error_by_step.csv")


@lru_cache(maxsize=None)
def model_info():
    path = OUTPUT_DIR / "model_info.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python -m modeling.run_pipeline` to create the forecasting outputs."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def clear_cache():
    """Forget cached outputs, e.g. after re-running the pipeline."""
    for fn in (forecasts_table, test_predictions_table, metrics_table, error_by_step_table, model_info):
        fn.cache_clear()
