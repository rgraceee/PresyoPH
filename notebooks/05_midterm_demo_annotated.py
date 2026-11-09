# =============================================================================
# PresyoPH – Midterm System Demonstration (annotated Python version)
# =============================================================================
# This is a standalone script version of notebooks/05_midterm_demonstration.ipynb.
# It runs end-to-end: loads cleaned CSVs, fits CPI forecasting models,
# evaluates them, selects the best model, and produces final forecasts.
#
# Prerequisites:
#   1. Run data_pipeline/preprocess_*.py  -> creates datasets/processed/*.csv
#   2. Run modeling/run_pipeline.py        -> creates datasets/outputs/model_info.json
#   3. Working directory must be the PresyoPH project root (C:\PresyoPH).
# =============================================================================

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Setup: make the project root importable so `modeling` package resolves.
# If run from inside the notebooks/ folder, use its parent as root.
# ---------------------------------------------------------------------------
ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Internal PresyoPH modules
from modeling import config            # global settings (dates, horizons, models, metrics)
from modeling.models import fit_all    # fits ARIMA, Linear Regression, MA, ETS on training data
from modeling import evaluation as ev  # metrics, rolling origin, model selection, forecast helpers
from modeling.derive import derive_all # PSA formulas: inflation = (CPI_t/CPI_t-12 - 1)*100; pp = 100/CPI_t

# Paths to cleaned data and output folders
PROC = ROOT / 'datasets' / 'processed'
OUT  = ROOT / 'datasets' / 'outputs'

# Plot style and pandas float display
plt.rcParams.update({'figure.figsize': (11, 4), 'axes.grid': True, 'grid.alpha': 0.3})
pd.set_option('display.float_format', '{:.3f}'.format)

print('Project root:', ROOT)
print('Target series:', config.TARGET_AREA, '-', config.TARGET_ITEM)
print('Data period:', config.DATA_START.date(), 'to', config.DATA_END.date())
print('Eligible models:', config.PROPOSAL_MODELS)
print('Extra (reported only):', config.EXTRA_MODELS)

# =============================================================================
# PART 2: DATA PREPARATION AND PREPROCESSING
# =============================================================================

# Load the four cleaned CSVs produced by data_pipeline/preprocess_*.py
# Each file is one row per observation (date, area, category/indicator, value).
cpi_raw    = pd.read_csv(PROC / 'cpi_clean.csv',    parse_dates=['date'])
inf_raw    = pd.read_csv(PROC / 'inflation_clean.csv', parse_dates=['date'])
pp_raw     = pd.read_csv(PROC / 'purchasing_power_clean.csv', parse_dates=['date'])
fies_raw   = pd.read_csv(PROC / 'fies_clean.csv')

# Inventory table: rows, unique areas, categories, months, missing values, duplicates
inventory = pd.DataFrame([
    {'dataset': 'CPI',                      'rows': len(cpi_raw),    'areas': cpi_raw['area'].nunique(), 'categories': cpi_raw['category'].nunique(), 'months': cpi_raw['date'].nunique(), 'missing': int(cpi_raw['value'].isna().sum()), 'duplicates': int(cpi_raw.duplicated(subset=['date','area','category']).sum())},
    {'dataset': 'Inflation',                'rows': len(inf_raw),    'areas': inf_raw['area'].nunique(), 'categories': inf_raw['category'].nunique(), 'months': inf_raw['date'].nunique(), 'missing': int(inf_raw['value'].isna().sum()), 'duplicates': int(inf_raw.duplicated(subset=['date','area','category']).sum())},
    {'dataset': 'Purchasing power',         'rows': len(pp_raw),     'areas': pp_raw['area'].nunique(),  'categories': np.nan,                'months': pp_raw['date'].nunique(), 'missing': int(pp_raw['value'].isna().sum()), 'duplicates': int(pp_raw.duplicated(subset=['date','area']).sum())},
    {'dataset': 'FIES 2023',                'rows': len(fies_raw),   'areas': fies_raw['area'].nunique(), 'categories': np.nan,             'months': np.nan,                'missing': int(fies_raw.isna().sum().sum()), 'duplicates': int(fies_raw.duplicated(subset=['year','area','income_group','indicator']).sum())},
])
print(inventory.to_string(index=False))

# Print date ranges and a preview of the CPI data
print('CPI date range:', cpi_raw['date'].min().date(), 'to', cpi_raw['date'].max().date())
print('Inflation date range:', inf_raw['date'].min().date(), 'to', inf_raw['date'].max().date())
print('Purchasing power date range:', pp_raw['date'].min().date(), 'to', pp_raw['date'].max().date())
print('FIES year:', sorted(fies_raw['year'].unique()))
print()
print('CPI preview:')
print(cpi_raw.head(6).to_string(index=False))

# ---------------------------------------------------------------------------
# Extract the national all-items CPI series (the sole forecasting target)
#   - strip leading dots / whitespace from area names (PSA geographic-level codes)
#   - filter to PHILIPPINES + "0 - ALL ITEMS"
#   - set date as index, sort, enforce monthly frequency ('MS' = month start)
# ---------------------------------------------------------------------------
cpi = (
    cpi_raw.assign(area=cpi_raw['area'].str.lstrip('.').str.strip())
      .query("area == 'PHILIPPINES' and category == '0 - ALL ITEMS'")
      .set_index('date')['value']
      .sort_index()
      .asfreq('MS')
)
cpi.name = 'cpi'

print('National all-items CPI observations:', len(cpi))
print('Period:', cpi.index.min().date(), 'to', cpi.index.max().date())
print('Missing:', int(cpi.isna().sum()))
print(cpi.describe().to_frame().T.to_string())

# ---------------------------------------------------------------------------
# EDA: plot CPI with 12-month rolling mean; highlight the test period.
# Also print yearly first/last/mean and within-year % change.
# ---------------------------------------------------------------------------
fig, ax = plt.subplots()
ax.plot(cpi, label='CPI (All Items)')
ax.plot(cpi.rolling(12).mean(), label='12-month rolling mean', linestyle='--')
ax.axvspan(config.TEST_START, config.TEST_END, color='grey', alpha=0.15,
           label='Test set (Sep 2025 - Aug 2026)')
ax.set_title('National CPI, All Items (2018 = 100)')
ax.set_ylabel('Index')
ax.legend()
plt.show()

yearly = cpi.groupby(cpi.index.year).agg(['first', 'last', 'mean'])
yearly['change within year (%)'] = (yearly['last'] / yearly['first'] - 1) * 100
print(yearly.to_string())

# ---------------------------------------------------------------------------
# Data quality checks table (missing values, duplicates, coverage)
# ---------------------------------------------------------------------------
quality = pd.DataFrame([
    {'check': 'Missing values (CPI)',            'result': int(cpi_raw['value'].isna().sum()),                      'status': 'PASS' if cpi_raw['value'].isna().sum() == 0 else 'FAIL'},
    {'check': 'Missing values (Inflation)',      'result': int(inf_raw['value'].isna().sum()),                     'status': 'PASS' if inf_raw['value'].isna().sum() == 0 else 'FAIL'},
    {'check': 'Missing values (Purchasing power)','result': int(pp_raw['value'].isna().sum()),                    'status': 'PASS' if pp_raw['value'].isna().sum() == 0 else 'FAIL'},
    {'check': 'Missing values (FIES)',           'result': int(fies_raw.isna().sum().sum()),                       'status': 'PASS' if fies_raw.isna().sum().sum() == 0 else 'FAIL'},
    {'check': 'Duplicate observations (CPI)',    'result': int(cpi_raw.duplicated(subset=['date','area','category']).sum()), 'status': 'PASS' if cpi_raw.duplicated(subset=['date','area','category']).sum() == 0 else 'FAIL'},
    {'check': 'Duplicate observations (FIES)',   'result': int(fies_raw.duplicated(subset=['year','area','income_group','indicator']).sum()), 'status': 'PASS' if fies_raw.duplicated(subset=['year','area','income_group','indicator']).sum() == 0 else 'FAIL'},
    {'check': 'CPI months per area/category',    'result': int(cpi_raw.groupby(['area','category'])['date'].nunique().min()), 'status': 'PASS'},
    {'check': 'CPI expected vs actual rows',     'result': f"{len(cpi_raw)} vs {cpi_raw['area'].nunique()*cpi_raw['category'].nunique()*cpi_raw['date'].nunique()}", 'status': 'PASS' if len(cpi_raw) == cpi_raw['area'].nunique()*cpi_raw['category'].nunique()*cpi_raw['date'].nunique() else 'FAIL'},
])
print(quality.to_string(index=False))

# =============================================================================
# PART 3: ALGORITHM IMPLEMENTATION, MODEL DEVELOPMENT, AND EXPERIMENTATION
# =============================================================================

# Train / test split (time series: last 12 months = test, rest = train)
train = cpi[: config.TRAIN_END]
test  = cpi[config.TEST_START : config.TEST_END]

print(f'Train: {train.index[0]:%b %Y} - {train.index[-1]:%b %Y}  ({len(train)} months)')
print(f'Test:  {test.index[0]:%b %Y}  - {test.index[-1]:%b %Y}  ({len(test)} months)')
print(f'Split: {len(train)/len(cpi):.1%} / {len(test)/len(cpi):.1%}')

# Plot train/test split
fig, ax = plt.subplots()
ax.plot(train, label='Training data')
ax.plot(test, color='black', marker='o', markersize=3, label='Test data (withheld)')
ax.axvline(config.TEST_START, color='grey', linestyle='--')
ax.set_title('Train/test split of national CPI')
ax.set_ylabel('Index (2018 = 100)')
ax.legend()
plt.show()

# Fit all four models on training data only (exactly as in modeling/models.py)
results = fit_all(train, horizon=config.HORIZON)

# Show fitted parameters for each model
params = {name: r.params for name, r in results.items()}
print(pd.DataFrame(params).T.to_string())

# ---- ARIMA candidate selection (AIC + parsimony rule) ----
arima = results['ARIMA']
cand = arima.candidates.copy()
cand['order'] = cand['order'].astype(str)
cand['seasonal_order'] = cand['seasonal_order'].astype(str)
print(cand[['order','seasonal_order','aic','n_params','converged','selected']].sort_values('aic').reset_index(drop=True).to_string(index=False))
print('\nChosen ARIMA order:', arima.params['order'], '| seasonal:', arima.params['seasonal_order'],
      '| drift/month:', round(arima.params['drift_per_month'], 4))

# ---- Linear Regression fit diagnostics ----
from statsmodels.stats.stattools import durbin_watson

lr = results['Linear Regression']
print(f"CPI = {lr.params['intercept']:.3f} + {lr.params['slope_per_month']:.4f} x t   (R^2 = {lr.params['r_squared']:.3f})")
print('Durbin-Watson statistic: %.3f (near 2 = independent residuals)' % durbin_watson(lr.fitted.resid))

# Plot fitted trend line on training data
t = np.arange(1, len(train) + 1)
fig, ax = plt.subplots()
ax.plot(train, label='Training data')
ax.plot(train.index, lr.fitted.fittedvalues, color='tab:orange', label='Fitted trend line')
ax.set_title('Linear Regression: fitted trend on the training data')
ax.legend()
plt.show()

# ---- Moving Average window selection ----
ma = results['Moving Average']
print(f"Chosen window: k = {ma.params['k']}  ->  forecast level {ma.params['level']:.2f}")
print(ma.candidates.to_string(index=False))

# ---- ETS (extra, reported only) ----
ets = results['ETS']
print({k: v for k, v in ets.params.items()})
print(ets.candidates.to_string(index=False))

# ---- Residual diagnostics (ARIMA) ----
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.graphics.tsaplots import plot_acf

resid = arima.fitted.resid.iloc[1:]

fig, axes = plt.subplots(1, 3, figsize=(14, 3.5))
axes[0].plot(resid); axes[0].axhline(0, color='black', linewidth=0.8); axes[0].set_title('Residuals')
plot_acf(resid, lags=24, ax=axes[1], title='ACF of residuals')
axes[2].hist(resid, bins=20); axes[2].set_title('Distribution of residuals')
fig.tight_layout()
plt.show()

print(acorr_ljungbox(resid, lags=[6, 12, 24], return_df=True).to_string(index=False))

# ---- Test-period forecasts by model (with 95% prediction intervals) ----
COLORS = {'ARIMA': 'tab:blue', 'Linear Regression': 'tab:orange', 'Moving Average': 'tab:green', 'ETS': 'tab:purple'}
history = cpi['2023-01':config.TRAIN_END]

fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharey=True)
for ax, (name, r) in zip(axes.flat, results.items()):
    ax.plot(history, color='grey', label='Training data')
    ax.plot(test, color='black', marker='o', markersize=3, label='Actual (test)')
    ax.plot(r.forecast, color=COLORS[name], label='Forecast')
    ax.fill_between(r.forecast.index, r.lower, r.upper, color=COLORS[name], alpha=0.15,
                    label='95% interval')
    ax.axvline(config.TEST_START, color='grey', linestyle='--', linewidth=0.8)
    ax.set_title(name + (' (extra)' if name in config.EXTRA_MODELS else ''))
    ax.legend(fontsize=8, loc='upper left')
fig.suptitle('CPI forecasts for the test period (Sep 2025 - Aug 2026)')
fig.tight_layout()
plt.show()

forecast_table = pd.DataFrame({'actual': test, **{name: r.forecast for name, r in results.items()}})
print(forecast_table.round(2).to_string())

# =============================================================================
# PART 4: EXPERIMENTAL RESULTS AND EVALUATION
# =============================================================================

# Prepare derived actual series (inflation, purchasing power) for evaluation
inf_series = (
    inf_raw.assign(area=inf_raw['area'].str.lstrip('.').str.strip())
      .query("area == 'PHILIPPINES' and category == '0 - ALL ITEMS'")
      .set_index('date')['value']
      .sort_index()
      .asfreq('MS')
)
pp_series = (
    pp_raw.assign(area=pp_raw['area'].str.lstrip('.').str.strip())
      .query("area == 'PHILIPPINES'")
      .set_index('date')['value']
      .sort_index()
      .asfreq('MS')
)

actuals = {'cpi': cpi, 'inflation': inf_series, 'purchasing_power': pp_series}

# Main test forecasts (train Jan 2018 - Aug 2025, forecast Sep 2025 - Aug 2026)
_, main = ev.forecast_from(cpi, config.TRAIN_END)
main = ev.attach_actuals(main, actuals)

# Metrics per sub-period (full test, before shock, after shock)
for label, (start, end) in config.TEST_SUBPERIODS.items():
    m = ev.metrics_table(main, start, end)
    print('\n###', label)
    pivot = m.pivot(index='model', columns='variable', values=config.METRICS)
    pivot = pivot.swaplevel(axis=1)[[v for v in config.VARIABLES]]
    pivot = pivot.reindex(columns=config.METRICS, level=1).rename(columns={'cpi':'CPI','inflation':'Inflation','purchasing_power':'Purchasing power'}, level=0)
    print(pivot.reindex(config.PROPOSAL_MODELS + config.EXTRA_MODELS).round(3).to_string())

# Rolling-origin evaluation (5 earlier origins: Aug 2022 .. Aug 2024)
rolling, fold_metrics = ev.rolling_origin(cpi, actuals)
print('Average over the five rolling-origin folds (pooled CPI focus):')
avg = ev.average_over_folds(fold_metrics)
print(avg[avg['variable']=='cpi'].round(3).to_string(index=False))

# Pooled evaluation: all six origins (72 forecast months per model) — selection basis
pooled = pd.concat([rolling, main], ignore_index=True)
pooled_metrics = ev.metrics_table(pooled)
pivot = pooled_metrics.pivot(index='model', columns='variable', values=config.METRICS)
pivot = pivot.swaplevel(axis=1)[[v for v in config.VARIABLES]]
pivot = pivot.reindex(columns=config.METRICS, level=1).rename(columns={'cpi':'CPI','inflation':'Inflation','purchasing_power':'Purchasing power'}, level=0)
print(pivot.reindex(config.PROPOSAL_MODELS + config.EXTRA_MODELS).round(3).to_string())

# Model selection comparison (2-of-3-metrics rule; else lowest RMSE)
rows = []
for basis_label, metrics in [('Pooled, six origins (selection basis)', pooled_metrics),
                             ('Main test only (original plan)', ev.metrics_table(main, config.TEST_START, config.TEST_END))]:
    for label, models in [('proposal models', config.PROPOSAL_MODELS),
                          ('including ETS', config.PROPOSAL_MODELS + config.EXTRA_MODELS)]:
        winner, explanation, wins = ev.select_model(metrics, models=models)
        rows.append({'evaluation': basis_label, 'models': label, 'winner': winner, 'reason': explanation})
pd.set_option('display.max_colwidth', None)
print(pd.DataFrame(rows).to_string(index=False))

# Final model selection
final_model, explanation, wins, _ = ev.select_final_model(main, rolling)
print(f'Selection basis: {config.SELECTION_BASIS}')
print(f'Final model: {final_model}')
print(explanation)
print('Metric wins:', {k: int(v) for k, v in wins.items()})

# Error by forecast step (pooled over six origins)
MODEL_ORDER = config.PROPOSAL_MODELS + config.EXTRA_MODELS
by_step = ev.error_by_step(pooled)[MODEL_ORDER]
print(by_step.round(3).to_string())

fig, ax = plt.subplots(figsize=(10, 4))
for model in MODEL_ORDER:
    ax.plot(by_step.index, by_step[model], marker='o', markersize=3,
            color=COLORS[model],
            linestyle='--' if model in config.EXTRA_MODELS else '-',
            label=model + (' (extra)' if model in config.EXTRA_MODELS else ''))
ax.set_xlabel('Months ahead')
ax.set_ylabel('Mean absolute error (index points)')
ax.set_title('CPI error by forecast step, pooled over six origins')
ax.set_xticks(range(1, config.HORIZON + 1))
ax.legend()
plt.show()

# =============================================================================
# PART 5: FINAL FORECAST (refit on all data, Sep 2026 – Aug 2027)
# =============================================================================

# Refit selected model on full data and produce 12-month forecast
final_results, final_predictions = ev.forecast_from(cpi, config.DATA_END, models=[final_model])
final = final_results[final_model]
print(f'{final_model} settings on all data: {final.params}')

# Derive inflation and purchasing power from CPI forecast (PSA formulas)
final_table = derive_all(cpi, final.forecast)
final_table['cpi_lower'], final_table['cpi_upper'] = final.lower, final.upper
print(final_table.round(2).to_string())

# Confirm saved outputs and recorded final model
import json
info = json.loads((OUT / 'model_info.json').read_text(encoding='utf-8'))
print('\nSaved outputs:', [p.name for p in sorted(OUT.glob('*'))])
print('Final model recorded in model_info.json:', info['final_model'])

# ---- Final forecast visualization (3 panels: CPI, Inflation, Purchasing Power) ----
fig, axes = plt.subplots(1, 3, figsize=(15, 4))
history_start = '2023-01'
inf_hist = actuals['inflation']
pp_hist = actuals['purchasing_power']

axes[0].plot(cpi[history_start:], color='black', label='Actual')
axes[0].plot(final.forecast, color=COLORS[final_model], label='Forecast')
axes[0].fill_between(final.forecast.index, final.lower, final.upper, color=COLORS[final_model], alpha=0.15,
                     label='95% interval')
axes[0].set_title('CPI (2018 = 100)')
axes[0].legend(fontsize=8)

axes[1].plot(inf_hist[history_start:], color='black', label='Actual')
axes[1].plot(final_table['inflation'], color=COLORS[final_model], label='Forecast')
axes[1].set_title('Inflation (%) (derived from CPI)')
axes[1].legend(fontsize=8)

axes[2].plot(pp_hist[history_start:], color='black', label='Actual')
axes[2].plot(final_table['purchasing_power'], color=COLORS[final_model], label='Forecast')
axes[2].set_title('Purchasing power of the peso (derived from CPI)')
axes[2].legend(fontsize=8)

for ax in axes:
    ax.axvline(config.DATA_END, color='grey', linestyle='--', linewidth=0.8)
fig.suptitle(f'Final forecast, Sep 2026 - Aug 2027 ({final_model})')
fig.tight_layout()
plt.show()
