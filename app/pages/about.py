"""Supporting page: About / Methodology."""

import streamlit as st

from app.ui import shell, tokens
from backend import data


def render():
    shell.page_header("About PresyoPH", "Four PSA datasets in one place, so households, students, researchers, and planners "
                      "can see how the cost of living is changing and what may come next.")

    st.subheader("Data sources")
    st.markdown(f"""
{tokens.PSA_ATTRIBUTION} The data is public and aggregate; no personal information is used.

| Dataset | Coverage | Used for |
|---|---|---|
| [Consumer Price Index](https://statistics.bettergov.ph/datasets/4e9a668dd28bc2207b05) | Monthly, Jan 2018 – {data.get_date_range('cpi')[1]:%b %Y}; national, regions, 13 commodity groups | Trends, categories, regions, forecasting |
| [Inflation](https://statistics.bettergov.ph/datasets/f274aab864e785e2cc15) | Monthly, Jan 2019 – {data.get_date_range('inflation')[1]:%b %Y} | Trends, categories, regions |
| [Purchasing power of the peso](https://statistics.bettergov.ph/datasets/4aa816e60823b630d044) | Monthly, Jan 2018 – {data.get_date_range('purchasing_power')[1]:%b %Y} | Purchasing power page |
| [Family Income and Expenditure Survey (FIES)](https://statistics.bettergov.ph/datasets/9bf607fafa4d799669ad) | 2023 only; national and regions; 10 income groups | Household finances page |
""")

    st.subheader("Definitions")
    st.markdown("""
- **Consumer Price Index (CPI):** measures changes in the prices of goods and services households commonly buy.
- **Inflation rate:** the percentage change in prices compared with the same month a year earlier.
- **Purchasing power of the peso:** how much a peso can buy compared with the base year; it falls as prices rise.
- **FIES:** PSA's survey of how much Filipino families earn, spend, and save.
- **Income group (decile):** families ranked by income and split into ten equal groups, from the lowest-income tenth to the highest.
- **MAE, RMSE, MAPE:** forecast error measures; lower is better. MAPE is unreliable for inflation when inflation is near zero.
""")

    st.subheader("Methodology")
    info = data.get_model_info()
    st.markdown(f"""
- **Forecasting:** ARIMA, Linear Regression, and Moving Average were compared on national all-items CPI; the selected model is **{info['final_model']}**. Inflation and purchasing power forecasts are calculated from the CPI forecast using PSA's formulas, so all three variables are covered.
- **Evaluation:** models were tested on months they had not seen, using MAE, RMSE, and MAPE. Details are on the Forecasts and Model Comparison page.
- **Base year:** CPI and purchasing power use 2018 as the base year (2018 = 100). PSA moved from a 2012 base to 2018; the series used here is on the 2018 base throughout, so values from before and after the change are comparable.
""")

    st.subheader("Limitations")
    st.markdown("""
- Forecasts use historical CPI patterns only and cannot anticipate fuel prices, weather, disasters, or policy changes.
- FIES is a 2023 snapshot: it shows how income groups compare, not how their income, spending, or savings change over time, and it is not forecast.
- Categories are PSA's 13 commodity groups, not individual products.
- Regional comparisons depend on PSA's published regions; see the notes on that page.
""")


render()
