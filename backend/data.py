"""Backend functions for the PresyoPH dashboard (task 6).

Streamlit pages call these functions and never read files directly. Data
comes from backend/sources.py, so switching to Member 1's database does not
change anything here.

Conventions
- Indicators: "cpi" (index, 2018 = 100), "inflation" (year-on-year, %),
  "purchasing_power" (pesos, 2018 = 1.00).
- Dates are the first day of the month. `start` and `end` accept anything
  pandas can parse ("2020-01", "2020-01-01", a Timestamp) and are inclusive.
- Areas use PSA's names without the leading dots, e.g. "PHILIPPINES",
  "National Capital Region (NCR)".
- Functions return pandas DataFrames or plain dicts; invalid arguments raise
  ValueError with a message that can be shown to the user.
"""

import pandas as pd

from backend import sources

INDICATORS = ("cpi", "inflation", "purchasing_power")
NATIONAL = "PHILIPPINES"
ALL_ITEMS = "0 - ALL ITEMS"
FORECAST_HORIZONS = range(1, 13)
EVALUATIONS = ("pooled", "main_test", "rolling_fold", "rolling_average")

INDICATOR_LABELS = {
    "cpi": "Consumer Price Index (2018 = 100)",
    "inflation": "Inflation rate (%)",
    "purchasing_power": "Purchasing power of the peso",
}

# Short labels for the 13 commodity groups, keyed by PSA's code.
CATEGORY_LABELS = {
    "01": "Food and non-alcoholic beverages",
    "02": "Alcoholic beverages and tobacco",
    "03": "Clothing and footwear",
    "04": "Housing, water, electricity, gas and other fuels",
    "05": "Furnishings, household equipment and maintenance",
    "06": "Health",
    "07": "Transport",
    "08": "Information and communication",
    "09": "Recreation, sport and culture",
    "10": "Education services",
    "11": "Restaurants and accommodation services",
    "12": "Financial services",
    "13": "Personal care and miscellaneous goods and services",
}


# --- Validation helpers ------------------------------------------------------

def _check_indicator(indicator):
    if indicator not in INDICATORS:
        raise ValueError(f"Unknown indicator {indicator!r}. Choose one of: {', '.join(INDICATORS)}.")


def _check_horizon(horizon):
    if horizon not in FORECAST_HORIZONS:
        raise ValueError(f"Horizon must be between 1 and 12 months, got {horizon!r}.")


def _date(value):
    return None if value is None else pd.Timestamp(value)


def _filter_dates(frame, start, end, column="date"):
    if start is not None:
        frame = frame[frame[column] >= _date(start)]
    if end is not None:
        frame = frame[frame[column] <= _date(end)]
    return frame


def _category_code(item):
    return item.split(" - ", 1)[0]


def _category_label(item):
    return CATEGORY_LABELS.get(_category_code(item), item.split(" - ", 1)[-1].capitalize())


def _rows(indicator, area=None, item=None):
    _check_indicator(indicator)
    table = sources.price_table(indicator)
    if area is not None:
        rows = table[table["area"] == area]
        if rows.empty:
            raise ValueError(f"Unknown area {area!r}. See list_areas() for valid names.")
        table = rows
    if item is not None:
        rows = table[table["item"] == item]
        if rows.empty:
            raise ValueError(f"Unknown item {item!r}. See list_categories() for valid names.")
        table = rows
    return table


# --- Lists for filters -------------------------------------------------------

def list_areas(level=None):
    """Area names, optionally only one level: "national", "region",
    "area group" (Areas Outside NCR), or "province/city". Regions come in
    PSA order."""
    if level == "region":
        return sources.regions()
    table = sources.price_table("cpi")[["area", "area_level"]].drop_duplicates()
    if level is not None:
        if level not in set(table["area_level"]):
            raise ValueError(f"Unknown level {level!r}.")
        table = table[table["area_level"] == level]
    return table["area"].tolist()


def list_categories(include_all_items=False):
    """Commodity groups as a DataFrame with columns item (PSA's label, used
    as the filter value), code, and label (short display name)."""
    items = sorted(sources.price_table("cpi")["item"].unique())
    if not include_all_items:
        items = [i for i in items if i != ALL_ITEMS]
    return pd.DataFrame({
        "item": items,
        "code": [_category_code(i) for i in items],
        "label": ["All items" if i == ALL_ITEMS else _category_label(i) for i in items],
    })


def get_date_range(indicator="cpi"):
    """(first month, last month) available for an indicator."""
    dates = _rows(indicator)["date"]
    return dates.min(), dates.max()


# --- Historical series -------------------------------------------------------

def get_series(indicator, start=None, end=None, area=NATIONAL, item=ALL_ITEMS):
    """One monthly series. Columns: date, value."""
    if indicator == "purchasing_power":
        item = ALL_ITEMS
    rows = _filter_dates(_rows(indicator, area, item), start, end)
    return rows[["date", "value"]].sort_values("date").reset_index(drop=True)


def get_cpi(start=None, end=None, area=NATIONAL, item=ALL_ITEMS):
    """Monthly CPI (2018 = 100). Columns: date, value."""
    return get_series("cpi", start, end, area, item)


def get_inflation(start=None, end=None, area=NATIONAL, item=ALL_ITEMS):
    """Monthly year-on-year inflation (%). Columns: date, value."""
    return get_series("inflation", start, end, area, item)


def get_purchasing_power(start=None, end=None, area=NATIONAL):
    """Monthly purchasing power of the peso. Columns: date, value."""
    return get_series("purchasing_power", start, end, area)


def get_series_wide(indicator, start=None, end=None, areas=None, items=None):
    """Several series side by side, for comparison charts.

    Pass several `areas` (one item) or several `items` (one area). Defaults:
    areas = [PHILIPPINES], items = [all items]. Returns a DataFrame indexed by
    date with one column per area or item.
    """
    areas = areas or [NATIONAL]
    items = items or [ALL_ITEMS]
    if len(areas) > 1 and len(items) > 1:
        raise ValueError("Compare several areas or several items, not both.")
    frames = {}
    for area in areas:
        for item in items:
            key = area if len(areas) > 1 else (item if len(items) > 1 else area)
            frames[key] = get_series(indicator, start, end, area, item).set_index("date")["value"]
    return pd.DataFrame(frames)


def get_period_stats(indicator, start=None, end=None, area=NATIONAL, item=ALL_ITEMS):
    """Highest, lowest, and average value over a period, plus the change from
    its first to its last month."""
    series = get_series(indicator, start, end, area, item)
    if series.empty:
        raise ValueError("No data in the selected period.")
    values = series.set_index("date")["value"]
    first, last = values.iloc[0], values.iloc[-1]
    return {
        "indicator": indicator,
        "start": values.index[0],
        "end": values.index[-1],
        "months": len(values),
        "highest": {"value": values.max(), "date": values.idxmax()},
        "lowest": {"value": values.min(), "date": values.idxmin()},
        "average": values.mean(),
        "first": first,
        "last": last,
        "change": round(last - first, 6),
        "percent_change": (last / first - 1) * 100 if first else None,
    }


def get_latest(area=NATIONAL):
    """Latest value of each indicator and its change from the previous month,
    for summary cards."""
    out = {}
    for indicator in INDICATORS:
        values = get_series(indicator, area=area).set_index("date")["value"]
        latest, previous = values.iloc[-1], values.iloc[-2]
        out[indicator] = {
            "date": values.index[-1],
            "value": latest,
            "previous": previous,
            # Rounded to remove floating-point noise (e.g. -0.10000000000000053).
            "change": round(latest - previous, 6),
        }
    return out


# --- Categories ----------------------------------------------------------------

def get_category_comparison(indicator="inflation", date=None, area=NATIONAL):
    """The 13 commodity groups at one month (default: latest), ranked from
    highest to lowest. Columns: rank, item, code, label, value. The all-items
    value for the same month is in the frame's attrs["all_items"]."""
    rows = _rows(indicator, area)
    date = _date(date) if date is not None else rows["date"].max()
    month = rows[rows["date"] == date]
    if month.empty:
        raise ValueError(f"No {indicator} data for {date:%B %Y}.")

    all_items = month.loc[month["item"] == ALL_ITEMS, "value"]
    groups = month[month["item"] != ALL_ITEMS].sort_values("value", ascending=False)
    out = pd.DataFrame({
        "rank": range(1, len(groups) + 1),
        "item": groups["item"].values,
        "code": [_category_code(i) for i in groups["item"]],
        "label": [_category_label(i) for i in groups["item"]],
        "value": groups["value"].values,
    })
    out.attrs.update({"date": date, "indicator": indicator, "area": area,
                      "all_items": all_items.iloc[0] if not all_items.empty else None})
    return out


def get_top_category(date=None, area=NATIONAL):
    """The commodity group with the highest year-on-year inflation, for the
    Home page's 'biggest recent price increase' card."""
    ranking = get_category_comparison("inflation", date, area)
    top = ranking.iloc[0]
    return {
        "date": ranking.attrs["date"],
        "item": top["item"],
        "label": top["label"],
        "inflation": top["value"],
        "all_items_inflation": ranking.attrs["all_items"],
    }


# --- Regions ---------------------------------------------------------------------

def get_regional_comparison(indicator="inflation", date=None, item=ALL_ITEMS, regions=None):
    """Regions at one month (default: latest), ranked from highest to lowest.
    Columns: rank, region, value, difference_from_national."""
    rows = _rows(indicator, item=ALL_ITEMS if indicator == "purchasing_power" else item)
    date = _date(date) if date is not None else rows["date"].max()
    month = rows[rows["date"] == date]
    if month.empty:
        raise ValueError(f"No {indicator} data for {date:%B %Y}.")

    regions = regions or sources.regions()
    unknown = set(regions) - set(sources.regions())
    if unknown:
        raise ValueError(f"Unknown region(s): {', '.join(sorted(unknown))}.")

    national = month.loc[month["area"] == NATIONAL, "value"].iloc[0]
    regional = month[month["area"].isin(regions)].sort_values("value", ascending=False)
    out = pd.DataFrame({
        "rank": range(1, len(regional) + 1),
        "region": regional["area"].values,
        "value": regional["value"].values,
        "difference_from_national": regional["value"].values - national,
    })
    out.attrs.update({"date": date, "indicator": indicator, "national": national})
    return out


# --- FIES (household finances) ---------------------------------------------------

def get_fies(areas=None, deciles=None, level=None):
    """2023 FIES average income, expenditure, and savings in thousand pesos
    (constant 2021 prices). Columns: area, area_level, decile, income,
    expenditure, savings, savings_rate (% of income)."""
    table = sources.fies_table()
    if level is not None:
        table = table[table["area_level"] == level]
    if areas is not None:
        unknown = set(areas) - set(table["area"])
        if unknown:
            raise ValueError(f"Unknown FIES area(s): {', '.join(sorted(unknown))}.")
        table = table[table["area"].isin(areas)]
    if deciles is not None:
        table = table[table["decile"].isin(deciles)]
    table = table.assign(savings_rate=table["savings"] / table["income"] * 100)
    return table.sort_values(["area", "decile"]).reset_index(drop=True)


def get_fies_by_decile(area=NATIONAL):
    """One area's 11 income groups (all, then first to tenth decile)."""
    return get_fies(areas=[area]).reset_index(drop=True)


def get_fies_by_region(decile="All Income Groups"):
    """The 18 regions for one income group, in PSA order."""
    table = get_fies(level="region", deciles=[decile])
    order = {name: i for i, name in enumerate(sources.regions())}
    return table.sort_values("area", key=lambda s: s.map(order)).reset_index(drop=True)


# --- Forecasts and model results -------------------------------------------------

def get_final_model():
    """Name of the model selected in task 4."""
    return sources.model_info()["final_model"]


def get_model_info():
    """Selection rule and result, data period, and model settings."""
    return sources.model_info()


def get_forecast(variable="cpi", horizon=12, model=None):
    """Forecast for the next `horizon` months (1-12) from the selected model,
    or from `model` if given. Columns: date, step, forecast, lower, upper
    (95% prediction interval)."""
    _check_indicator(variable)
    _check_horizon(horizon)
    table = sources.forecasts_table()
    if model is None:
        rows = table[table["is_selected"]]
    else:
        rows = table[table["model"] == model]
        if rows.empty:
            raise ValueError(f"Unknown model {model!r}. Choose one of: {', '.join(table['model'].unique())}.")
    rows = rows[(rows["variable"] == variable) & (rows["step"] <= horizon)]
    return rows[["date", "step", "forecast", "lower", "upper"]].sort_values("step").reset_index(drop=True)


def get_next_month_forecast(variable="cpi"):
    """The first forecast month, for the Home page card."""
    row = get_forecast(variable, horizon=1).iloc[0]
    return {"date": row["date"], "forecast": row["forecast"], "lower": row["lower"],
            "upper": row["upper"], "model": get_final_model()}


def get_model_metrics(variable=None, evaluation="pooled", period=None):
    """MAE, RMSE, and MAPE per model. `evaluation` is "pooled" (used for
    selection), "main_test", "rolling_fold", or "rolling_average"; `period`
    narrows main_test or rolling_fold rows (see metrics.csv). Columns: model,
    variable, period, mae, rmse, mape, n_months, is_selected_model,
    in_proposal."""
    if evaluation not in EVALUATIONS:
        raise ValueError(f"Unknown evaluation {evaluation!r}. Choose one of: {', '.join(EVALUATIONS)}.")
    table = sources.metrics_table()
    rows = table[table["evaluation"] == evaluation]
    if variable is not None:
        _check_indicator(variable)
        rows = rows[rows["variable"] == variable]
    if period is not None:
        rows = rows[rows["period"] == period]
        if rows.empty:
            raise ValueError(f"Unknown period {period!r} for evaluation {evaluation!r}.")
    eligible = set(sources.model_info()["selection"]["eligible_models"])
    rows = rows.assign(in_proposal=rows["model"].isin(eligible))
    return rows[["model", "variable", "period", "mae", "rmse", "mape", "n_months",
                 "is_selected_model", "in_proposal"]].reset_index(drop=True)


def get_test_predictions(variable="cpi", evaluation="main_test", model=None):
    """Forecasts made during evaluation, with actual values, for
    actual-vs-forecast charts. Columns: origin, model, date, step, forecast,
    lower, upper, actual, error."""
    _check_indicator(variable)
    if evaluation not in ("main_test", "rolling_origin"):
        raise ValueError("evaluation must be 'main_test' or 'rolling_origin'.")
    table = sources.test_predictions_table()
    rows = table[(table["evaluation"] == evaluation) & (table["variable"] == variable)]
    if model is not None:
        rows = rows[rows["model"] == model]
    return rows[["origin", "model", "date", "step", "forecast", "lower", "upper", "actual", "error"]].reset_index(drop=True)


def get_error_by_step(variable="cpi", model=None):
    """Mean absolute error at each step ahead (1-12), pooled over all
    evaluation origins. Columns: model, step, mae."""
    _check_indicator(variable)
    table = sources.error_by_step_table()
    rows = table[table["variable"] == variable]
    if model is not None:
        rows = rows[rows["model"] == model]
    return rows[["model", "step", "mae"]].reset_index(drop=True)
