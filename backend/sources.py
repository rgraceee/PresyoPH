"""Where the backend gets its data. The only module to change when Member 1's
database is ready.

Historical data currently comes from the temporary loader, which reads the
raw PSA exports. Forecasting outputs come from datasets/outputs/, written by
modeling/run_pipeline.py. To switch to the database, reimplement these
functions with the same names and return columns; nothing in backend/data.py
needs to change.

All functions are cached. Callers must not modify the returned frames.
"""
import os
import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

from modeling import temp_loader

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "datasets" / "outputs"


@lru_cache(maxsize=None)
def price_table(indicator):
    """Columns: area, area_level, item, date, value."""
    import mysql.connector

    tables = {
        "cpi": "cpi",
        "inflation": "inflation",
        "purchasing_power": "purchasing_power",
    }

    if indicator not in tables:
        raise ValueError(f"Unknown indicator: {indicator}")

    conn = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "presyoph_db"),
    port=int(os.getenv("DB_PORT", "3306"))
)

    try:
        if indicator == "purchasing_power":
            query = """
                SELECT a.area_name AS area,
                       '0 - ALL ITEMS' AS item,
                       p.date,
                       p.value
                FROM purchasing_power p
                JOIN areas a ON p.area_id = a.area_id
            """
        else:
            query = f"""
                SELECT a.area_name AS area,
                       c.category_name AS item,
                       p.date,
                       p.value
                FROM {tables[indicator]} p
                JOIN areas a ON p.area_id = a.area_id
                JOIN categories c ON p.category_id = c.category_id
            """

        cursor = conn.cursor()
        try:
            cursor.execute(query)
            data = pd.DataFrame(
                cursor.fetchall(),
                columns=["area", "item", "date", "value"]
            )
        finally:
            cursor.close()
    finally:
        conn.close()

    def area_level(raw_name):
        if raw_name == "PHILIPPINES":
            return "national"
        name = raw_name.lstrip(".")
        if name.startswith("Areas Outside"):
            return "area group"
        if len(raw_name) - len(name) <= 2:
            return "region"
        return "province/city"

    data["area_level"] = data["area"].map(area_level)
    data["area"] = data["area"].str.lstrip(".").str.strip()
    data["date"] = pd.to_datetime(data["date"])
    data["value"] = pd.to_numeric(data["value"])

    return data[["area", "area_level", "item", "date", "value"]]


@lru_cache(maxsize=None)
def fies_table():
    """Columns: area, area_level, decile, income, expenditure, savings."""
    import mysql.connector

    conn = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "presyoph_db"),
    port=int(os.getenv("DB_PORT", "3306"))
)

    try:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT area, income_group, indicator, value
                FROM fies
                WHERE year = 2023
            """)
            data = pd.DataFrame(
                cursor.fetchall(),
                columns=["area", "decile", "indicator", "value"]
            )
        finally:
            cursor.close()
    finally:
        conn.close()

    data["area"] = (
        data["area"].str.replace(r"\d+/$", "", regex=True)
        .str.lstrip(".").str.strip()
    )
    data["indicator"] = (
        data["indicator"]
        .str.extract(r"Average (\w+)", expand=False)
        .str.lower()
    )
    data["value"] = pd.to_numeric(data["value"])

    wide = data.pivot_table(
        index=["area", "decile"],
        columns="indicator",
        values="value",
        aggfunc="first"
    ).reset_index()

    wide.columns.name = None

    is_region = wide["area"].isin(temp_loader.FIES_REGION_NAMES)
    wide["area_level"] = "province/city"
    wide.loc[is_region, "area_level"] = "region"
    wide.loc[wide["area"] == "PHILIPPINES", "area_level"] = "national"

    wide["area"] = wide["area"].replace(temp_loader.FIES_REGION_NAMES)

    # Align province/city names with the CPI area labels.
    cpi_areas = price_table("cpi")["area"].unique()
    area_lookup = {name.upper(): name for name in cpi_areas}
    wide["area"] = wide["area"].map(
        lambda name: area_lookup.get(name.upper(), name)
    )

    wide["decile"] = pd.Categorical(
        wide["decile"],
        categories=temp_loader.FIES_DECILES,
        ordered=True
    )

    return wide[
        ["area", "area_level", "decile", "income", "expenditure", "savings"]
    ]


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
