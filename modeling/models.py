"""CPI forecasting models: ARIMA, Linear Regression, Moving Average, ETS."""

import itertools
import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.exponential_smoothing.ets import ETSModel

from modeling import config


@dataclass
class ForecastResult:
    model: str
    forecast: pd.Series
    lower: pd.Series
    upper: pd.Series
    params: dict = field(default_factory=dict)
    candidates: pd.DataFrame = field(default_factory=pd.DataFrame)
    fitted: object = None

    def to_frame(self):
        return pd.DataFrame({
            "model": self.model,
            "forecast": self.forecast,
            "lower": self.lower,
            "upper": self.upper,
        })


def _future_index(train, horizon):
    return pd.date_range(train.index[-1] + pd.offsets.MonthBegin(1), periods=horizon, freq="MS")


def _alpha():
    return 1 - config.INTERVAL_LEVEL


def _select_by_aic(rows):
    """Pick a candidate by AIC with the parsimony rule."""
    table = pd.DataFrame(rows)
    usable = table[table["converged"] & table["aic"].notna()]
    if usable.empty:
        raise RuntimeError("No candidate model converged")
    best_aic = usable["aic"].min()
    table["delta_aic"] = table["aic"] - best_aic
    supported = usable[usable["aic"] <= best_aic + config.AIC_TOLERANCE]
    chosen = supported.sort_values(["n_params", "aic"]).index[0]
    table["selected"] = table.index == chosen
    return chosen, table.sort_values("aic").reset_index(drop=True)


# --- ARIMA ---

def fit_arima(train, horizon=config.HORIZON):
    """Fit ARIMA(p, 1, q) with drift; p, q and seasonal part chosen by AIC."""
    rows, fits = [], []
    for p, q, seasonal in itertools.product(
        config.ARIMA_P_VALUES, config.ARIMA_Q_VALUES, config.ARIMA_SEASONAL_CANDIDATES
    ):
        order = (p, config.ARIMA_D, q)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                fitted = ARIMA(train, order=order, seasonal_order=seasonal, trend="t").fit()
            except (ValueError, np.linalg.LinAlgError):
                fitted = None
        converged = fitted is not None and not any(
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

    chosen, candidates = _select_by_aic(rows)
    fitted = fits[chosen]
    order, seasonal = rows[chosen]["order"], rows[chosen]["seasonal_order"]

    index = _future_index(train, horizon)
    pred = fitted.get_forecast(horizon)
    ci = pred.conf_int(alpha=_alpha())
    return ForecastResult(
        model="ARIMA",
        forecast=pd.Series(pred.predicted_mean.values, index=index),
        lower=pd.Series(ci.iloc[:, 0].values, index=index),
        upper=pd.Series(ci.iloc[:, 1].values, index=index),
        params={
            "order": order,
            "seasonal_order": seasonal,
            "aic": fitted.aic,
            "drift_per_month": float(fitted.params.iloc[0]),
        },
        candidates=candidates,
        fitted=fitted,
    )


# --- Linear Regression ---

def fit_linear_regression(train, horizon=config.HORIZON):
    """Fit CPI regressed on a time index using OLS."""
    t = np.arange(1, len(train) + 1)
    fitted = sm.OLS(train.values, sm.add_constant(t)).fit()

    t_future = np.arange(len(train) + 1, len(train) + horizon + 1)
    frame = fitted.get_prediction(sm.add_constant(t_future)).summary_frame(alpha=_alpha())

    index = _future_index(train, horizon)
    intercept, slope = fitted.params
    return ForecastResult(
        model="Linear Regression",
        forecast=pd.Series(frame["mean"].values, index=index),
        lower=pd.Series(frame["obs_ci_lower"].values, index=index),
        upper=pd.Series(frame["obs_ci_upper"].values, index=index),
        params={"intercept": intercept, "slope_per_month": slope, "r_squared": fitted.rsquared},
        fitted=fitted,
    )


# --- Moving Average ---

def _ma_errors(series, k, horizon):
    values = series.values
    errors = {h: [] for h in range(1, horizon + 1)}
    for origin in range(k - 1, len(values) - 1):
        level = values[origin - k + 1: origin + 1].mean()
        for h in range(1, horizon + 1):
            if origin + h < len(values):
                errors[h].append(values[origin + h] - level)
    return errors


def fit_moving_average(train, horizon=config.HORIZON):
    """Flat forecast equal to the mean of the last k months; k chosen by validation RMSE."""
    fit_part = train.iloc[: -config.VALIDATION_MONTHS]
    validation = train.iloc[-config.VALIDATION_MONTHS:]

    rows = []
    for k in config.MA_WINDOWS:
        level = fit_part.iloc[-k:].mean()
        rmse = np.sqrt(np.mean((validation.values - level) ** 2))
        rows.append({"k": k, "validation_rmse": rmse})
    candidates = pd.DataFrame(rows).sort_values("validation_rmse").reset_index(drop=True)
    k = int(candidates.loc[0, "k"])

    level = train.iloc[-k:].mean()
    index = _future_index(train, horizon)
    forecast = pd.Series(level, index=index)

    errors = _ma_errors(train, k, horizon)
    lo_q, hi_q = _alpha() / 2, 1 - _alpha() / 2
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


# --- ETS ---

def fit_ets(train, horizon=config.HORIZON):
    """ETS with additive trend, damped or not, chosen by AIC."""
    rows, fits = [], []
    for damped in config.ETS_DAMPED_OPTIONS:
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

    chosen, candidates = _select_by_aic(rows)
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


MODELS = {
    "ARIMA": fit_arima,
    "Linear Regression": fit_linear_regression,
    "Moving Average": fit_moving_average,
    "ETS": fit_ets,
}


def fit_all(train, horizon=config.HORIZON, models=None):
    names = models or list(MODELS)
    return {name: MODELS[name](train, horizon) for name in names}
