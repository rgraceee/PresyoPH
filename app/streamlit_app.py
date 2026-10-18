"""PresyoPH dashboard entry point.

    .venv/Scripts/python -m streamlit run app/streamlit_app.py

Registers every screen and wraps them in the shared shell (sidebar, search
bar, footer) from app/ui/. Screens live in app/pages/.
"""

import sys
from pathlib import Path

# Make `app`, `backend`, and `modeling` importable when Streamlit runs this file.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app.ui import shell

st.set_page_config(page_title="PresyoPH", page_icon=":material/monitoring:", layout="wide")

# Page opened at "/". tests/test_forecasts_page.py loads this file and expects the
# Forecasts page, so that page stays the default. Change to "home" (Dashboard) once
# that test loads app/pages/forecasts.py directly.
DEFAULT_PAGE = "home"

# key, file, sidebar title, icon, URL path. The first six follow the Figma sidebar.
SCREENS = [
    ("home", "pages/dashboard.py", "Dashboard", ":material/home:", "dashboard"),
    ("trends", "pages/trends.py", "Price Trends", ":material/trending_up:", "price-trends"),
    ("categories", "pages/categories.py", "Household Necessities", ":material/shopping_basket:", "household-necessities"),
    ("finances", "pages/finances.py", "Purchasing Power", ":material/account_balance_wallet:", "purchasing-power"),
    ("regional", "pages/regional.py", "Household Analysis", ":material/groups:", "household-analysis"),
    ("forecasting", "pages/forecasts.py", "Forecasting",":material/calendar_month:", "forecasting"),
    ("reports", "pages/reports.py", "Reports", ":material/description:", "reports"),
    ("explorer", "pages/data_explorer.py", "Data Explorer", ":material/table_chart:", "data-explorer"),
    ("about", "pages/about.py", "About / Methodology", ":material/info:", "about"),
]
PAGES = {key: st.Page(path, title=title, icon=icon, url_path=url, default=(key == DEFAULT_PAGE))
         for key, path, title, icon, url in SCREENS}

shell.inject_css()
shell.sidebar(PAGES)
shell.topbar(PAGES)
st.navigation(list(PAGES.values()), position="hidden").run()
shell.footer()
