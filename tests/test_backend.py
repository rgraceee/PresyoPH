"""Tests for backend/data.py. Run with:  .venv/Scripts/python -m pytest

They read the raw PSA files and datasets/outputs/, so run the pipeline
(`python -m modeling.run_pipeline`) first.
"""

import pandas as pd
import pytest

from backend import data

LAST_MONTH = pd.Timestamp("2026-08-01")
NCR = "National Capital Region (NCR)"


# --- Historical series -----------------------------------------------------------

def test_national_cpi_covers_full_period():
    cpi = data.get_cpi()
    assert len(cpi) == 104
    assert cpi["date"].min() == pd.Timestamp("2018-01-01")
    assert cpi["date"].max() == LAST_MONTH
    assert cpi["value"].iloc[0] == 97.2
    assert cpi["value"].iloc[-1] == 136.4


def test_date_filter_is_inclusive():
    cpi = data.get_cpi(start="2020-01", end="2020-12")
    assert len(cpi) == 12
    assert cpi["date"].iloc[0] == pd.Timestamp("2020-01-01")
    assert cpi["date"].iloc[-1] == pd.Timestamp("2020-12-01")


def test_inflation_starts_2019():
    assert data.get_inflation()["date"].min() == pd.Timestamp("2019-01-01")


def test_purchasing_power_is_reciprocal_of_cpi():
    cpi = data.get_cpi().set_index("date")["value"]
    pp = data.get_purchasing_power().set_index("date")["value"]
    assert ((100 / cpi).round(2) - pp).abs().max() < 1e-9


def test_regional_and_category_series():
    assert len(data.get_cpi(area=NCR)) == 104
    food = data.get_inflation(item="01 - FOOD AND NON-ALCOHOLIC BEVERAGES")
    assert len(food) == 92


def test_series_wide_compares_areas():
    wide = data.get_series_wide("inflation", start="2026-01", areas=["PHILIPPINES", NCR])
    assert list(wide.columns) == ["PHILIPPINES", NCR]
    assert len(wide) == 8


def test_series_wide_rejects_areas_and_items_together():
    with pytest.raises(ValueError):
        data.get_series_wide("cpi", areas=["PHILIPPINES", NCR],
                             items=["0 - ALL ITEMS", "07 - TRANSPORT"])


@pytest.mark.parametrize("call", [
    lambda: data.get_cpi(area="Atlantis"),
    lambda: data.get_cpi(item="99 - NOTHING"),
    lambda: data.get_series("gdp"),
])
def test_invalid_arguments_raise_value_error(call):
    with pytest.raises(ValueError):
        call()


# --- Summaries -------------------------------------------------------------------

def test_lists_for_filters():
    assert len(data.list_areas("region")) == 18
    assert data.list_areas("national") == ["PHILIPPINES"]
    categories = data.list_categories()
    assert len(categories) == 13
    assert categories["code"].tolist() == [f"{i:02d}" for i in range(1, 14)]


def test_latest_values():
    latest = data.get_latest()
    assert latest["cpi"]["date"] == LAST_MONTH
    assert latest["cpi"]["value"] == 136.4
    assert latest["cpi"]["change"] == pytest.approx(0.8)
    assert latest["inflation"]["value"] == 6.1
    assert set(latest) == set(data.INDICATORS)


def test_period_stats():
    stats = data.get_period_stats("cpi", start="2026-01", end="2026-08")
    assert stats["highest"]["value"] == 136.5
    assert stats["highest"]["date"] == pd.Timestamp("2026-04-01")
    assert stats["lowest"]["value"] == 131.0
    assert stats["months"] == 8


def test_category_comparison_is_ranked():
    ranking = data.get_category_comparison()
    assert len(ranking) == 13
    assert ranking["value"].is_monotonic_decreasing
    assert ranking["rank"].tolist() == list(range(1, 14))
    assert ranking.attrs["all_items"] == 6.1


def test_top_category_matches_ranking():
    top = data.get_top_category()
    assert top["item"] == data.get_category_comparison().iloc[0]["item"]


@pytest.mark.parametrize("indicator", data.INDICATORS)
def test_regional_comparison(indicator):
    table = data.get_regional_comparison(indicator)
    assert len(table) == 18
    assert table["value"].is_monotonic_decreasing
    national = table.attrs["national"]
    assert (table["value"] - national - table["difference_from_national"]).abs().max() < 1e-9


# --- FIES ------------------------------------------------------------------------

def test_fies_by_decile():
    table = data.get_fies_by_decile()
    assert len(table) == 11
    assert table["decile"].iloc[0] == "All Income Groups"
    assert table.loc[0, "income"] == 314.82


def test_fies_by_region_uses_cpi_region_names():
    table = data.get_fies_by_region()
    assert table["area"].tolist() == data.list_areas("region")
    assert (table["savings_rate"] > 0).all()


# --- Forecasts and model results -------------------------------------------------

@pytest.mark.parametrize("horizon", [3, 6, 12])
@pytest.mark.parametrize("variable", data.INDICATORS)
def test_forecast_horizons(variable, horizon):
    forecast = data.get_forecast(variable, horizon)
    assert len(forecast) == horizon
    assert forecast["date"].iloc[0] == pd.Timestamp("2026-09-01")
    assert (forecast["lower"] <= forecast["forecast"]).all()
    assert (forecast["forecast"] <= forecast["upper"]).all()


def test_forecast_rejects_invalid_horizon():
    with pytest.raises(ValueError):
        data.get_forecast("cpi", 24)


def test_selected_model_is_used_by_default():
    final = data.get_final_model()
    assert data.get_forecast("cpi").equals(data.get_forecast("cpi", model=final))


def test_next_month_forecast():
    nxt = data.get_next_month_forecast()
    assert nxt["date"] == pd.Timestamp("2026-09-01")
    assert nxt["model"] == data.get_final_model()


def test_pooled_metrics_support_the_selection():
    metrics = data.get_model_metrics("cpi")
    assert len(metrics) == 4
    proposal = metrics[metrics["in_proposal"]]
    best = proposal.loc[proposal["rmse"].idxmin(), "model"]
    assert best == data.get_final_model()
    assert metrics.loc[metrics["is_selected_model"], "model"].tolist() == [best]


def test_main_test_metrics_by_period():
    rows = data.get_model_metrics("cpi", "main_test", "full test (Sep 2025 - Aug 2026)")
    assert (rows["n_months"] == 12).all()


def test_test_predictions_and_error_by_step():
    preds = data.get_test_predictions("cpi", "main_test", model="ARIMA")
    assert len(preds) == 12
    assert preds["actual"].notna().all()
    steps = data.get_error_by_step("cpi", model="ARIMA")
    assert steps["step"].tolist() == list(range(1, 13))
