"""PresyoPH dashboard entry point.

    .venv/Scripts/python -m streamlit run app/streamlit_app.py

Placeholder until Member 3's app structure is ready: it only registers the
Forecasts page. Member 3 adds the other screens to the navigation below.
"""

import sys
from pathlib import Path

# Make `app`, `backend`, and `modeling` importable when Streamlit runs this file.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(page_title="PresyoPH", page_icon=":material/monitoring:", layout="wide")

pages = [
    st.Page("pages/forecasts.py", title="Forecasts", icon=":material/trending_up:"),
]
st.navigation(pages).run()
