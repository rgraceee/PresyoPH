"""Tests for backend/sources.py. Run with:  .venv/Scripts/python -m pytest

They need MySQL running with presyoph_db imported (see README.md).
"""

import pandas as pd
import pytest

from backend import sources

NCR = "National Capital Region (NCR)"
FOOD = "01 - FOOD AND NON-ALCOHOLIC BEVERAGES"


@pytest.mark.parametrize("indicator, start", [
    ("cpi", "2018-01-01"),
    ("inflation", "2019-01-01"),
    ("purchasing_power", "2018-01-01"),
])
def test_series_is_monthly_and_complete(indicator, start):
    values = sources.series(indicator)
    assert values.name == indicator
    assert values.index.freqstr == "MS"
    assert values.index[0] == pd.Timestamp(start)
    assert values.index[-1] == pd.Timestamp("2026-08-01")
    assert values.dtype == float
    assert values.notna().all()


def test_series_matches_price_table():
    table = sources.price_table("cpi")
    rows = table[(table["area"] == NCR) & (table["item"] == FOOD)].sort_values("date")
    values = sources.series("cpi", area=NCR, item=FOOD)
    assert values.tolist() == rows["value"].tolist()
    assert values.index.tolist() == rows["date"].tolist()


@pytest.mark.parametrize("call", [
    lambda: sources.series("cpi", area="Atlantis"),
    lambda: sources.series("cpi", item="99 - NOTHING"),
    lambda: sources.series("gdp"),
])
def test_series_rejects_unknown_arguments(call):
    with pytest.raises(ValueError):
        call()


def test_unreachable_database_gives_setup_hint(monkeypatch):
    monkeypatch.setenv("DB_PORT", "1")  # nothing listens on port 1
    with pytest.raises(ConnectionError, match="XAMPP"):
        sources._query("SELECT 1", ["one"])
