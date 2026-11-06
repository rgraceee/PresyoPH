# PresyoPH - Project Summary

## 1. What PresyoPH Is

PresyoPH is a Streamlit dashboard that helps Filipino households, students, researchers, and planners understand how the cost of living is changing in the Philippines. It displays monthly Consumer Price Index (CPI), inflation rate, and purchasing power of the peso data from the Philippine Statistics Authority (PSA), breaks it down by region and commodity group, and provides CPI forecasts using statistical models. It also includes 2023 Family Income and Expenditure Survey (FIES) data showing how income, spending, and savings compare across income groups.

## 2. Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.13 | Main programming language |
| Streamlit | 1.64.0 | Web dashboard framework - builds the UI, pages, and interactive controls |
| pandas | 3.0.6 | Data manipulation - DataFrames for all data processing and analysis |
| numpy | 2.5.3 | Numerical computing - math operations used by models and metrics |
| statsmodels | 0.15.0 | Statistical models - ARIMA and ETS forecasting |
| plotly | 7.1.0 | Interactive charts - all graphs and figures in the dashboard |
| mysql-connector-python | 26.7.0 | Database driver - connects Python to the MySQL database |
| scikit-learn | 1.9.1 | ML utilities - available for modeling support |
| matplotlib | 3.11.2 | Plotting - available for charting |
| openpyxl | 3.1.5 | Excel reading - reads raw Excel source files in the data pipeline |
| pytest | 9.1.1 | Testing - runs the test suite |
| MySQL / MariaDB (via XAMPP) | - | Database - stores cleaned CPI, inflation, purchasing power, FIES, areas, and categories data |

**Why each is used**: Streamlit provides the user interface; pandas and numpy handle data; statsmodels builds the forecast models; plotly renders charts; mysql-connector-python reads from the database; pytest validates correctness.

## 3. Folder and File Structure

```
PresyoPH/
├── app/                          # Streamlit dashboard (UI layer)
│   ├── streamlit_app.py          # Entry point: registers pages, sidebar, navigation
│   ├── theme.py                  # Colours, number formats, and indicator labels
│   ├── __init__.py               # Package marker
│   ├── ui/                       # Shared UI components
│   │   ├── __init__.py           # Package marker
│   │   ├── shell.py              # Sidebar, top bar, search, KPI cards, insight cards, footer
│   │   ├── charts.py             # Plotly chart builders (forecast, time series, ranked bars)
│   │   ├── layout.py             # Month pickers, area options, page footer
│   │   ├── queries.py            # Extra data helpers (region groups, category changes, table export)
│   │   ├── tokens.py             # Figma colours, FIES wording, PSA attribution, disclaimer
│   │   ├── assets/               # Brand images (logo, sidebar illustration)
│   │   └── static/               # Custom CSS (presyoph.css)
│   ├── components/               # Reusable chart components
│   │   ├── __init__.py           # Package marker
│   │   └── forecast_charts.py    # Plotly figures for the Forecasts page
│   └── pages/                    # Individual dashboard screens
│       ├── __init__.py           # Package marker
│       ├── dashboard.py          # Home: KPI cards, trends, forecast, insights
│       ├── trends.py             # Cost-of-living trends (CPI + inflation over time)
│       ├── categories.py         # Household necessities by commodity group
│       ├── finances.py           # Purchasing power and FIES household finances
│       ├── regional.py           # Regional comparison of CPI, inflation, purchasing power
│       ├── forecasts.py          # Forecasting and model comparison
│       ├── reports.py            # Generate and download reports (Markdown + CSV)
│       ├── data_explorer.py      # Browse and download raw data tables
│       └── about.py              # About / methodology and limitations
├── backend/                      # Data access layer (pages never read files directly)
│   ├── __init__.py               # Package marker
│   ├── data.py                   # High-level data functions (series, stats, categories, regions, FIES, forecasts, metrics)
│   └── sources.py                # Low-level data access (MySQL queries, CSV output reading, caching)
├── modeling/                     # CPI forecasting models
│   ├── __init__.py               # Package marker
│   ├── config.py                 # Evaluation setup: splits, horizons, model settings, selection rule
│   ├── derive.py                 # Derive inflation and purchasing power from CPI forecasts
│   ├── evaluation.py             # Scoring (MAE, RMSE, MAPE) and model selection
│   ├── models.py                 # Model implementations: ARIMA, Linear Regression, Moving Average, ETS
│   └── run_pipeline.py           # Runs the full forecasting pipeline and saves outputs
├── data_pipeline/                # ETL scripts (preprocessing, loading, validation)
│   ├── preprocess_cpi.py         # Cleans raw CPI Excel files into cpi_clean.csv
│   ├── preprocess_inflation.py   # Cleans raw Inflation Excel files into inflation_clean.csv
│   ├── preprocess_fies.py        # Cleans raw FIES CSV into fies_clean.csv
│   ├── preprocess_purchasing_power.py  # Cleans raw Purchasing Power Excel into purchasing_power_clean.csv
│   ├── load_database.py          # Loads cleaned CSVs into the MySQL database
│   ├── validate_database.py      # Validates database integrity (counts, duplicates, foreign keys, dates, NULLs)
│   ├── validate_csv_mysql.py     # Compares cleaned CSV against MySQL data
│   └── validate_process.py       # Validates processed datasets before loading
├── database/                     # MySQL schema and data dump
│   ├── schema.sql                # Table definitions (areas, categories, cpi, inflation, purchasing_power, fies)
│   └── presyoph_db.sql           # Full database dump with schema and data
├── datasets/                     # Cleaned data and model outputs
│   ├── raw/                      # Raw source files (Excel CSVs from PSA)
│   ├── processed/                # Cleaned CSVs ready for database loading
│   └── outputs/                  # Model outputs: forecasts.csv, metrics.csv, model_info.json, etc.
├── tests/                        # pytest test suite
│   ├── test_backend.py           # Tests for backend/data.py
│   ├── test_sources.py           # Tests for backend/sources.py
│   └── test_forecasts_page.py    # Tests for the Forecasting page
├── docs/                         # Additional documentation
│   ├── data_preprocessing.md
│   ├── historical_trends.md
│   ├── modeling_method_and_results.md
│   └── system_evaluation_plan.md
├── reports/                      # Generated report figures
├── requirements.txt              # Python dependencies
├── pytest.ini                    # Pytest configuration
└── README.md                     # Setup and running instructions
```

## 4. How It Works (Main Flow)

1. **User opens the app** - `streamlit run app/streamlit_app.py` starts Streamlit, which loads the shared shell (sidebar, top bar, footer) and shows the Dashboard page by default.
2. **Data is fetched** - Pages call `backend/data.py` functions, which read from `backend/sources.py`. `sources.py` queries the MySQL database (`presyoph_db`) for historical data, or reads CSV files from `datasets/outputs/` for forecasts and model results. All results are cached.
3. **Prices are displayed** - The Dashboard shows KPI cards (CPI, inflation, purchasing power, household spending), a price trend chart, a 3-month forecast, regional comparison, and top price increases.
4. **User navigates** - The sidebar lets users switch between Dashboard, Price Trends, Household Necessities, Purchasing Power, Regional Comparison, Forecasting, Reports, Data Explorer, and About.
5. **Forecasting** - The Forecasts page shows CPI/inflation/purchasing power forecasts from the selected model (ARIMA, Linear Regression, or Moving Average), with 95% prediction intervals and model comparison metrics.
6. **Reports** - Users can generate Markdown/CSV reports on cost of living, commodity trends, household finances, regional comparison, or forecast results.
7. **Data pipeline (offline)** - Raw Excel/CSV files from PSA are cleaned by `data_pipeline/preprocess_*.py` scripts, loaded into MySQL by `load_database.py`, and validated by `validate_*.py` scripts. The forecasting pipeline (`modeling/run_pipeline.py`) produces forecast outputs.

## 5. Key Features

| Feature | Files / Functions |
|---------|-------------------|
| Dashboard KPI cards | `app/pages/dashboard.py` - `summary_cards()`, `data.get_latest()` |
| Price trend chart | `app/pages/dashboard.py` - `price_trend_card()`, `data.get_series()` |
| CPI forecast | `app/pages/forecasts.py` - `chart_card()`, `data.get_forecast()` |
| Model comparison | `app/pages/forecasts.py` - `results_card()`, `data.get_model_metrics()` |
| Category analysis | `app/pages/categories.py` - `data.get_category_comparison()`, `queries.get_category_changes()` |
| Purchasing power | `app/pages/finances.py` - `data.get_purchasing_power()`, `data.get_fies_by_decile()` |
| Regional comparison | `app/pages/regional.py` - `data.get_regional_comparison()` |
| Reports generation | `app/pages/reports.py` - `build_report()`, 5 report builders |
| Data explorer | `app/pages/data_explorer.py` - `queries.get_table()`, CSV download |
| Forecast model training | `modeling/models.py` - `fit_arima()`, `fit_linear_regression()`, `fit_moving_average()`, `fit_ets()` |
| Model selection | `modeling/evaluation.py` - `select_model()`, `select_final_model()` |
| Inflation/purchasing power derivation | `modeling/derive.py` - `to_inflation()`, `to_purchasing_power()` |
| Pipeline execution | `modeling/run_pipeline.py` - `run()` |
| Data loading | `data_pipeline/load_database.py` - loads CSVs into MySQL |
| Data validation | `data_pipeline/validate_database.py`, `validate_process.py`, `validate_csv_mysql.py` |

## 6. Function and Component Reference

| Name | File | Purpose | Inputs | Output |
|------|------|---------|--------|--------|
| `get_series` | `backend/data.py` | One monthly time series | indicator, start, end, area, item | DataFrame (date, value) |
| `get_cpi` | `backend/data.py` | Monthly CPI series | start, end, area, item | DataFrame (date, value) |
| `get_inflation` | `backend/data.py` | Monthly inflation series | start, end, area, item | DataFrame (date, value) |
| `get_purchasing_power` | `backend/data.py` | Monthly purchasing power series | start, end, area | DataFrame (date, value) |
| `get_latest` | `backend/data.py` | Latest value of each indicator | area | dict |
| `get_category_comparison` | `backend/data.py` | 13 commodity groups ranked by value | indicator, date, area | DataFrame (rank, item, code, label, value) |
| `get_top_category` | `backend/data.py` | Highest-inflation commodity group | date, area | dict |
| `get_regional_comparison` | `backend/data.py` | Regions ranked by indicator value | indicator, date, item, regions | DataFrame (rank, region, value, difference_from_national) |
| `get_fies` | `backend/data.py` | FIES income/spending/savings by area and decile | areas, deciles, level | DataFrame |
| `get_forecast` | `backend/data.py` | Forecast for next N months | variable, horizon, model | DataFrame (date, step, forecast, lower, upper) |
| `get_model_metrics` | `backend/data.py` | MAE, RMSE, MAPE per model | variable, evaluation, period | DataFrame |
| `get_model_info` | `backend/sources.py` | Selected model and selection details | - | dict |
| `price_table` | `backend/sources.py` | Cached price data from MySQL | indicator | DataFrame (area, area_level, item, date, value) |
| `forecasts_table` | `backend/sources.py` | Cached forecast outputs | - | DataFrame |
| `metrics_table` | `backend/sources.py` | Cached model metrics | - | DataFrame |
| `run_pipeline` | `modeling/run_pipeline.py` | Full forecasting pipeline | - | CSV files + model_info.json |
| `fit_arima` | `modeling/models.py` | Fit ARIMA model | train series, horizon | ForecastResult |
| `fit_linear_regression` | `modeling/models.py` | Fit trend regression | train series, horizon | ForecastResult |
| `fit_moving_average` | `modeling/models.py` | Fit moving average | train series, horizon | ForecastResult |
| `select_model` | `modeling/evaluation.py` | Choose best model by 2-of-3 rule | metrics, variable, models | (winner, explanation, wins) |
| `to_inflation` | `modeling/derive.py` | CPI to inflation conversion | CPI series | Series |
| `to_purchasing_power` | `modeling/derive.py` | CPI to purchasing power conversion | CPI series | Series |
| `summary_cards` | `app/pages/dashboard.py` | Render 4 KPI cards | latest, fies_all | (Streamlit UI) |
| `price_trend_card` | `app/pages/dashboard.py` | Render category trend chart | labels | (Streamlit UI) |
| `forecast_card` | `app/pages/dashboard.py` | Render 3-month forecast card | latest | (Streamlit UI) |
| `dual_axis_figure` | `app/pages/trends.py` | CPI + inflation dual-axis chart | cpi, inflation, height | Plotly Figure |
| `category_trend_figure` | `app/pages/categories.py` | Category CPI vs average chart | series, average, name | Plotly Figure |
| `trend_figure` | `app/pages/finances.py` | Purchasing power trend chart | series, label | Plotly Figure |
| `ranking_card` | `app/pages/regional.py` | Regional ranking HTML table | ranking, indicator, selected, suffix | (Streamlit UI) |
| `chart_card` | `app/pages/forecasts.py` | Historical vs forecast chart | variable, horizon, forecast, model, show_other | (Streamlit UI) |
| `results_card` | `app/pages/forecasts.py` | Forecast results table | variable, horizon, forecast, latest, model | (Streamlit UI) |
| `build_report` | `app/pages/reports.py` | Generate a report | kind, month, area | dict |
| `render` | `app/pages/*.py` | Render each page | - | (Streamlit UI) |
| `shell` | `app/ui/shell.py` | Shared UI: sidebar, top bar, cards, footer | - | (Streamlit UI) |
| `charts` | `app/ui/charts.py` | Plotly chart builders | data | Plotly Figures |

## 7. Data

**Source**: All data comes from the Philippine Statistics Authority (PSA) via OpenSTAT (statistics.bettergov.ph). The data is public and aggregate; no personal information is used.

**Datasets**:
- **Consumer Price Index (CPI)**: Monthly, Jan 2018 – Aug 2026; national, 18 regions, 120 areas, 13 commodity groups. Base year 2018 = 100. ~174,720 rows.
- **Inflation rate**: Monthly, Jan 2019 – Aug 2026; same areas and categories. ~154,560 rows.
- **Purchasing power of the peso**: Monthly, Jan 2018 – Aug 2026; national and areas. ~12,480 rows.
- **FIES (Family Income and Expenditure Survey)**: 2023 only; national and regions; 10 income deciles. 4,554 rows.

**Storage**: Data is stored in a MySQL database (`presyoph_db`) with tables: `areas`, `categories`, `cpi`, `inflation`, `purchasing_power`, `fies`. The database is set up using `database/schema.sql` and populated with `database/presyoph_db.sql`. Cleaned CSVs are in `datasets/processed/`, and model outputs are in `datasets/outputs/`.

**How data is used**: The backend (`backend/sources.py`) queries MySQL and returns DataFrames. `backend/data.py` provides higher-level functions for filtering, aggregation, and forecasts. Pages call `backend/data.py` functions and never read files directly, so switching data sources doesn't require page changes.

## 8. Possible Panelist Questions and Answers

**Q: What is PresyoPH?**
A: It's a dashboard that shows Philippine price data (CPI, inflation, purchasing power) and household spending data (FIES), with forecasts for future prices.

**Q: Where does the data come from?**
A: All data is from the Philippine Statistics Authority (PSA), accessed through OpenSTAT. It's public, aggregate data with no personal information.

**Q: What can users do with the app?**
A: Users can view current prices and inflation, compare commodity categories, see regional differences, check household finances by income group, view CPI forecasts, and download reports.

**Q: How are forecasts made?**
A: Only CPI is directly forecast using ARIMA, Linear Regression, or Moving Average models. Inflation and purchasing power are then calculated from the CPI forecast using PSA's official formulas, so all three forecasts are consistent.

**Q: Which model was selected and why?**
A: The selected model is shown in `datasets/outputs/model_info.json`. Models were evaluated on MAE, RMSE, and MAPE across multiple time periods, and the best one was chosen using a rule where a model must win on at least 2 of 3 metrics, otherwise the lowest RMSE wins.

**Q: Are the forecasts reliable?**
A: They are statistical estimates based only on historical CPI patterns. They cannot predict fuel prices, weather, disasters, or policy changes. The app includes a disclaimer about this.

**Q: What is FIES data and why is it included?**
A: FIES is the 2023 Family Income and Expenditure Survey. It shows how much Filipino families earn, spend, and save across 10 income groups. It's a snapshot, not a trend, so it's not forecast.

**Q: Can the app be run without a database?**
A: No. MySQL (via XAMPP) must be running with the `presyoph_db` database imported. The dashboard reads live data from the database.

**Q: How do I run the app?**
A: Install requirements with `pip install -r requirements.txt`, start MySQL in XAMPP, import `database/presyoph_db.sql`, then run `streamlit run app/streamlit_app.py`.

## 9. Known Issues / Incomplete Parts / Next Steps

- **ETS model**: ETS is implemented and reported but is not eligible for selection (not in the original proposal). It becomes eligible only if the instructor approves.
- **Database setup required**: The app needs MySQL running and the database imported before it will work. First-time users must follow the README setup steps.
- **Forecast outputs must be generated**: `datasets/outputs/` must exist (run `python -m modeling.run_pipeline` first) before the Forecasts page works.
- **No item-level prices**: Categories are PSA's 13 commodity groups only. Individual products (rice, cooking oil, etc.) are not in the dataset.
- **FIES is 2023 only**: It's a snapshot and not updated monthly or forecast.
- **Regional FIES by income group**: Not available; FIES regional data is shown separately from income-group data.
- **Missing brand assets**: `app/ui/assets/logo.svg/png` and `sidebar_illustration.svg/png` are referenced but may not exist; the sidebar falls back to text if missing.
- **Next steps**: Add ETS to eligible models (if approved), add more commodity detail, update FIES when newer data is available, add user accounts/preferences.
