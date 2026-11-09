# ETS removal notes

ETS was removed from the active forecasting implementation, dashboard labels, model configuration, and published forecast CSV/JSON outputs. The retained models are ARIMA, Linear Regression, and Moving Average.

The CSV outputs were filtered to retain the existing independently computed results for the three models. They were **not retrained** in this environment. For full reproduction, run `python -m modeling.run_pipeline` with the project database configured, then `python -m pytest`.

The existing Jupyter notebooks and historical report figures are preserved as original research artifacts; some may still show ETS comparisons. Update/re-execute those if they are to be presented as current three-model results.
