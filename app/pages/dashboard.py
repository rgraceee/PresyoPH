"""
================================================================================
FILE: app/pages/dashboard.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
Screen 1: Dashboard - the home/landing page of PresyoPH. It shows an at-a-glance
summary of the latest cost of living data:

  - Four KPI cards: CPI, inflation rate, purchasing power, average household spending
  - Price trend chart for selected categories
  - 3-month CPI forecast
  - Regional CPI comparison
  - Top 5 categories with biggest price increases
  - Savings rate by income decile
  - Key insights text

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- app/streamlit_app.py: Registers this page as the "home" page (default page).
- backend/data.py: Calls data.get_latest(), data.get_series(), data.get_cpi(),
  data.get_category_comparison(), data.get_regional_comparison(), data.get_top_category(),
  data.get_fies_by_decile(), data.get_forecast(), data.get_model_info(),
  data.get_date_range(), data.list_categories().
- backend/sources.py: Indirectly, through backend/data.py.
- app/ui/shell.py: Calls shell.kpi_card(), shell.panel_header(), shell.insight_card(),
  shell.mini_card(), shell.ranked_list(), shell.rank_color(), shell.rank_legend(),
  shell.page_header(), shell.greeting().
- app/ui/charts.py: Calls charts.time_series_figure(), charts.forecast_figure(),
  charts.banded_column_figure(), charts.ranked_bar_figure().
- app/ui/queries.py: Calls queries.get_category_changes().
- app/ui/theme.py: Calls theme.format_value().
- app/ui/tokens.py: Calls tokens.DECILE_SHORT.
- app/ui/layout.py: Calls month_label().

================================================================================
"""

"""Screen 1: Dashboard. The at-a-glance page (Figma: Dashboard)."""

import pandas as pd                                  # pandas: DataFrame operations
import streamlit as st                               # streamlit: UI components (columns, containers, etc.)

from app import theme                                # theme: format_value() for number formatting
from app.ui import charts, queries, shell, tokens    # charts: Plotly figures; queries: data helpers; shell: UI components; tokens: decile labels
from app.ui.layout import month_label                # month_label: format dates as "Aug 2026"
from backend import data                             # backend: all data access functions

# Default categories shown in the price trend chart (most relevant to households).
TREND_GROUPS = ["Food and non-alcoholic beverages", "Housing, water, electricity, gas and other fuels",
                "Transport", "Health"]

# Time period options for the trend chart: label -> number of months (None = all data).
PERIODS = {"6 months": 6, "12 months": 12, "24 months": 24, "All": None}


def summary_cards(latest, fies_all):
    """Show four KPI cards: CPI, inflation, purchasing power, average spending.
    
    Parameters
    ----------
    latest : dict
        Output of data.get_latest(); keys are "cpi", "inflation", "purchasing_power".
        Each value is a dict with keys: date, value, previous, change.
    fies_all : pandas.Series
        The "All Income Groups" row from data.get_fies_by_decile().
        Contains income, expenditure, savings columns.
    """
    cpi, infl, power = latest["cpi"], latest["inflation"], latest["purchasing_power"]  # Extract each indicator's data
    cols = st.columns(4)                                 # Create 4 equal-width columns for the cards
    with cols[0]:                                        # Card 1: CPI
        shell.kpi_card("Cost of Living Index", theme.format_value("cpi", cpi["value"]), "CPI", tone="green",
                       delta=f"{'▲' if cpi['change'] >= 0 else '▼'} {abs(cpi['change']):.1f} pts",  # Up/down arrow + change
                       bad=cpi["change"] > 0,           # Red if CPI went up (bad for consumers), green if down
                       help="Consumer Price Index, 2018 = 100. A CPI of 136 means prices are about 36% above 2018.",
                       foot=f"vs. {month_label(cpi['date'] - pd.DateOffset(months=1))}")  # Compare to previous month
    with cols[1]:                                        # Card 2: Inflation Rate
        shell.kpi_card("Inflation Rate", theme.format_value("inflation", infl["value"]), "%", tone="deep",
                       delta=f"{'▲' if infl['change'] >= 0 else '▼'} {abs(infl['change']):.1f} pts", bad=infl["change"] > 0,
                       help="How much higher prices are than in the same month a year earlier.", foot="vs. last month")
    with cols[2]:                                        # Card 3: Purchasing Power
        shell.kpi_card("Peso Purchasing Power", theme.format_value("purchasing_power", power["value"]), "₱", tone="gold",
                       delta=f"{'▲' if power['change'] >= 0 else '▼'} {abs(power['change']):.2f}", bad=power["change"] < 0,
                       # Red if purchasing power went down (bad), green if up (good)
                       help=f"Today's peso buys what about {power['value'] * 100:.0f} centavos bought in 2018.",
                       foot="vs. last month")
    with cols[3]:                                        # Card 4: Average Household Spending (FIES)
        shell.kpi_card("Average Household Spending", f"₱{fies_all['expenditure']:,.1f}k", "₱", tone="sage",
                       help="From the 2023 Family Income and Expenditure Survey (thousand pesos per family). "
                            "A 2023 snapshot, not a monthly figure.",
                       foot="FIES 2023 snapshot")


def price_trend_card(labels):
    """Show a multi-line CPI chart for selected categories over a chosen period.
    
    Parameters
    ----------
    labels : list of str
        Category display labels to choose from in the multiselect.
    """
    with st.container(key="card_trend"):                 # Container for this card section
        head, pick = st.columns([3.2, 1], vertical_alignment="top")  # Header area (left) and controls (right)
        with head:
            shell.panel_header("Price Trend (Selected Categories)", "Consumer Price Index by household necessity")
        period = pick.selectbox("Period", list(PERIODS), index=1, key="home_period", label_visibility="collapsed")
        # User picks which categories to show; defaults to the 4 TREND_GROUPS that exist in labels
        chosen = st.multiselect("Categories", labels, default=[g for g in TREND_GROUPS if g in labels], key="home_groups",
                                label_visibility="collapsed", placeholder="Choose categories")
        if not chosen:                                   # User hasn't picked any categories yet
            st.info("Choose at least one category to see its price trend.")
            return                                       # Exit early, show nothing
        # Map display labels to PSA item codes for data lookup
        items = data.list_categories().set_index("label")["item"]
        _, end = data.get_date_range("cpi")              # Get the latest available date
        # Calculate start date based on selected period (None = all data from the beginning)
        start = None if PERIODS[period] is None else end - pd.DateOffset(months=PERIODS[period] - 1)
        # Build a DataFrame with one column per chosen category, indexed by date
        frame = pd.DataFrame({g: data.get_series("cpi", start, None, item=items[g]).set_index("date")["value"] for g in chosen})
        # Render the multi-line chart
        st.plotly_chart(charts.time_series_figure(frame, y_title="CPI (2018 = 100)", hover=".1f", height=300),
                        config={"displayModeBar": False})  # Hide Plotly's mode bar for cleaner look


def savings_card():
    """Show a bar chart of savings rate by income decile (FIES 2023)."""
    with st.container(key="card_savings"):
        shell.panel_header("Savings by Household Income Group",
                           "Share of income saved, FIES 2023 (bottom 10% to top 10% of earners)", icon="house")
        # Get FIES data, exclude "All Income Groups" row (we want individual deciles only)
        groups = data.get_fies_by_decile().query("decile != 'All Income Groups'")
        # Convert decile names to short labels for the x-axis
        labels = [tokens.DECILE_SHORT[d] for d in groups["decile"]]
        # Bar chart: savings rate (%) by income decile
        st.plotly_chart(charts.banded_column_figure(labels, groups["savings_rate"], suffix="%", height=300),
                        config={"displayModeBar": False})


def regional_card():
    """Show a ranked bar chart of CPI by region for the latest month."""
    with st.container(key="card_regions"):
        # Get latest CPI date for the subtitle
        shell.panel_header("Cost of Living by Region", f"Consumer Price Index, {month_label(data.get_date_range('cpi')[1])}", icon="pin")
        ranking = data.get_regional_comparison("cpi")    # Get all regions ranked by CPI
        # Assign colours: higher CPI = worse (warm colours) since higher_is_better=False
        colors = [shell.rank_color(i, len(ranking), higher_is_better=False) for i in range(len(ranking))]
        # Build horizontal bar chart, with national value as reference line
        fig = charts.ranked_bar_figure(ranking["region"].str.replace(r"\s*\(.*\)", "", regex=True), ranking["value"],
                                       reference=ranking.attrs["national"], hover=".1f", height=420)
        fig.update_traces(marker_color=colors)           # Apply rank-based colours to bars
        st.plotly_chart(fig, config={"displayModeBar": False})
        shell.rank_legend(higher_is_better=False)        # Show colour legend (higher CPI = worse)


def top_increases_card():
    """Show the top 5 categories with the biggest one-month CPI rise."""
    with st.container(key="card_top"):
        shell.panel_header("Top 5 Price Increases (1 Month)", "Household necessities with the biggest CPI rise", icon="wallet")
        changes = queries.get_category_changes(1)        # Get 1-month CPI changes for all commodity groups
        # Build rows for the ranked list widget
        rows = [{"rank": r["rank"], "name": r["label"], "sub": f"CPI {r['value']:.1f}", "change": r["change_pct"]}
                for _, r in changes.head(5).iterrows()]  # Top 5 only
        shell.ranked_list(rows)                          # Render the ranked list
        # Show the date range covered
        st.caption(f"{month_label(changes.attrs['start'])} to {month_label(changes.attrs['end'])}.")


def insights_card(latest, top, ranking):
    """Show key insights: top category, purchasing power change, regional spread.
    
    Parameters
    ----------
    latest : dict
        Output of data.get_latest().
    top : dict
        Output of data.get_top_category().
    ranking : pandas.DataFrame
        Output of data.get_regional_comparison("cpi").
    """
    power = latest["purchasing_power"]                   # Purchasing power data
    hi, lo = ranking.iloc[0], ranking.iloc[-1]           # Highest and lowest CPI regions
    changes = queries.get_category_changes(1)            # Latest 1-month category changes
    top_month = changes.iloc[0]                          # Category with biggest increase
    items = [
        # Insight 1: Which category has highest inflation
        ("Rising prices in " + top["label"],
         f"Year-on-year inflation is {top['inflation']:.1f}%, against {top['all_items_inflation']:.1f}% for all items. "
         f"This month {top_month['label']} rose most ({top_month['change_pct']:+.1f}%)."),
        # Insight 2: Purchasing power trend
        ("Purchasing power " + ("declined" if power["change"] < 0 else "held or improved"),
         f"The peso's purchasing power is {power['value']:.2f}, {power['change']:+.2f} from last month."),
        # Insight 3: Regional spread
        ("Regional differences",
         f"CPI is highest in {hi['region']} ({hi['value']:.1f}) and lowest in {lo['region']} ({lo['value']:.1f})."),
    ]
    with st.container(key="insight_home"):
        shell.insight_card("Key Insights", items)        # Render the insights card
        st.page_link("pages/reports.py", label="View detailed report", icon=":material/arrow_forward:")  # Link to Reports
        st.caption("Generated automatically from the latest PSA data.")


def forecast_card(latest):
    """Show the 3-month CPI forecast and projected purchasing power."""
    with st.container(key="card_forecast"):
        shell.panel_header("Forecast (Next 3 Months)", "CPI forecast from the selected model, with 95% range")
        forecast = data.get_forecast("cpi", 3)           # Get 3-month CPI forecast
        # Get 12 months of history before the forecast starts (for chart context)
        history = data.get_series("cpi", start=forecast["date"].iloc[0] - pd.DateOffset(months=12))
        info = data.get_model_info()                     # Get model info (which model is selected)
        st.plotly_chart(charts.forecast_figure(history, forecast, "cpi", info["final_model"]),
                        config={"displayModeBar": False})
        # Projected purchasing power at the end of the forecast period
        pp = data.get_forecast("purchasing_power", 3).iloc[-1]
        now = latest["purchasing_power"]["value"]
        # Mini card showing projected purchasing power and % change from now
        shell.mini_card(f"Projected Purchasing Power ({month_label(pp['date'])})", f"{pp['forecast']:.2f}",
                        f"{'▲' if pp['forecast'] >= now else '▼'} {abs(pp['forecast'] / now - 1) * 100:.1f}%",
                        f"vs. {month_label(latest['purchasing_power']['date'])}", tone="green")


def render():
    """Render the full Dashboard page."""
    # Page header with greeting and subtitle
    shell.page_header(shell.greeting(),
                      "Here's the latest cost of living and purchasing power insights for Filipino households.")
    # Fetch all data needed by the cards
    latest = data.get_latest()                           # Latest values for all indicators
    fies_all = data.get_fies_by_decile().query("decile == 'All Income Groups'").iloc[0]  # All-income FIES row
    top = data.get_top_category()                        # Category with highest inflation
    ranking = data.get_regional_comparison("cpi")        # Regions ranked by CPI

    summary_cards(latest, fies_all)                      # Top row: 4 KPI cards
    labels = list(data.list_categories()["label"])       # All category labels for the multiselect
    price_trend_card(labels)                             # Price trend chart
    forecast_card(latest)                                # 3-month forecast
    region_col, top5_col = st.columns(2)                 # Two-column layout for bottom row
    with region_col:
        regional_card()                                  # Left: regional CPI ranking
    with top5_col:
        top_increases_card()                             # Right: top 5 price increases
    save_col, insight_col = st.columns(2)                # Two-column layout for bottom row
    with save_col:
        savings_card()                                   # Left: savings by decile
    with insight_col:
        insights_card(latest, top, ranking)              # Right: key insights


render()                                                 # Execute the page when Streamlit loads it
