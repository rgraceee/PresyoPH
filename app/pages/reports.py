"""
================================================================================
FILE: app/pages/reports.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
Reports screen: Generate and download analytics reports from PSA data. Five
report types are available:

  1. Cost-of-Living Summary - CPI, inflation, purchasing power for one month/area
  2. Commodity Price Trends - category changes over 6 months
  3. Household Purchasing Power - FIES data for one area
  4. Regional Comparison - all indicators by region
  5. CPI Forecast and Model Results - 12-month forecast + model metrics

Reports are generated on demand and offered as Markdown and CSV downloads.
Nothing is stored on a server -- reports exist only in the current browser
session.

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- app/streamlit_app.py: Registers this page as "reports".
- backend/data.py: Calls data.get_series(), data.get_purchasing_power(),
  data.get_fies_by_decile(), data.get_category_comparison(), data.get_regional_comparison(),
  data.get_forecast(), data.get_model_info(), data.get_model_metrics(),
  data.get_date_range(), data.INDICATORS, data.NATIONAL, data.list_areas(),
  data.ALL_ITEMS.
- app/ui/shell.py: Calls shell.page_header(), shell.pill(), shell.panel_header(),
  shell.esc().
- app/ui/layout.py: Calls area_label(), area_options(), month_label(), month_options().
- app/ui/queries.py: Calls queries.get_category_changes().
- app/ui/theme.py: Calls theme.INDICATOR_NAMES, theme.INDICATOR_SHORT_NAMES,
  theme.format_value().
- app/ui/tokens.py: Calls tokens.DECILE_SHORT, tokens.PSA_ATTRIBUTION,
  tokens.FORECAST_DISCLAIMER.

================================================================================
"""

"""Supporting screen: Reports (Figma: Reports and Report Details).

Reports are built on demand from the same backend data as the dashboard, then
offered as Markdown and CSV downloads. "Recent reports" lists the reports
generated in this browser session; nothing is stored on a server.
"""

from datetime import datetime                         # datetime: timestamp for report generation

import pandas as pd                                   # pandas: DataFrame operations
import streamlit as st                                # streamlit: UI components

from app import theme                                 # theme: indicator names, formats
from app.ui import queries, shell, tokens             # shell: UI components; queries: category changes; tokens: decile labels, attribution
from app.ui.layout import area_label, area_options, month_label, month_options  # UI helpers
from backend import data                              # backend: data access functions

# Available report types.
REPORT_TYPES = ["Cost-of-Living Summary", "Commodity Price Trends", "Household Purchasing Power",
                "Regional Comparison", "CPI Forecast and Model Results"]


def _md_table(table):
    """Convert a DataFrame to a Markdown table string.
    
    Parameters
    ----------
    table : pandas.DataFrame
        The table to convert.
    
    Returns
    -------
    str
        Markdown-formatted table.
    """
    header = "| " + " | ".join(map(str, table.columns)) + " |\n|" + "---|" * len(table.columns) + "\n"
    rows = "\n".join("| " + " | ".join(f"{v:,.2f}" if isinstance(v, float) else str(v) for v in row) + " |"
                     for row in table.itertuples(index=False))
    return header + rows


def _at(indicator, month, area):
    """Return the latest and previous values of an indicator at a given month.
    
    Parameters
    ----------
    indicator : str
        One of "cpi", "inflation", "purchasing_power".
    month : pandas.Timestamp
        The month to look up.
    area : str
        Area name.
    
    Returns
    -------
    tuple of (float, float or None)
        (current value, previous value).
    """
    series = data.get_series(indicator, end=month, area=area)  # Get series up to this month
    return series.iloc[-1]["value"], series.iloc[-2]["value"] if len(series) > 1 else None


def cost_of_living_summary(month, area):
    """Build a cost-of-living summary report for one month and area.
    
    Parameters
    ----------
    month : pandas.Timestamp
        The report month.
    area : str
        Area name.
    
    Returns
    -------
    tuple of (list of str, pandas.DataFrame)
        (findings, table).
    """
    findings = []
    for ind in data.INDICATORS:                            # One finding per indicator
        now, before = _at(ind, month, area)
        findings.append(f"{theme.INDICATOR_NAMES[ind]}: {theme.format_value(ind, now)} in {month_label(month)}"
                        + (f" ({now - before:+.2f} from the previous month)." if before is not None else "."))
    changes = queries.get_category_changes(1, month, area) # Category changes for this month
    top = changes.head(3)
    findings.append("Biggest one-month price rises: " + "; ".join(f"{r.label} ({r.change_pct:+.1f}%)" for r in top.itertuples()) + ".")
    cmp_cpi = data.get_category_comparison("cpi", month, area).set_index("label")["value"]  # CPI by category
    cmp_inf = data.get_category_comparison("inflation", month, area).set_index("label")["value"]  # Inflation by category
    table = pd.DataFrame({"CPI (2018=100)": cmp_cpi, "Inflation, year on year (%)": cmp_inf,
                          "Change vs previous month (%)": changes.set_index("label")["change_pct"]}).reset_index(names="Category")
    return findings, table


def commodity_trends(month, area):
    """Build a commodity price trends report for one month and area.
    
    Parameters
    ----------
    month : pandas.Timestamp
        The report month.
    area : str
        Area name.
    
    Returns
    -------
    tuple of (list of str, pandas.DataFrame)
        (findings, table).
    """
    changes = queries.get_category_changes(6, month, area).set_index("label")  # 6-month changes
    inflation = data.get_category_comparison("inflation", month, area).set_index("label")["value"]
    table = pd.DataFrame({"CPI (2018=100)": changes["value"], "6-month change (%)": changes["change_pct"],
                          "Inflation, year on year (%)": inflation}).reset_index(names="Category")
    fast, slow = changes.iloc[0], changes.iloc[-1]       # Fastest and slowest rising
    findings = [f"Fastest-rising category over six months: {changes.index[0]} ({fast['change_pct']:+.1f}%).",
                f"Slowest-rising category: {changes.index[-1]} ({slow['change_pct']:+.1f}%).",
                f"All items changed {changes.attrs['all_items']:+.1f}% over the same period."]
    return findings, table


def household_purchasing_power(month, area):
    """Build a household purchasing power report for one month and area.
    
    Parameters
    ----------
    month : pandas.Timestamp
        The report month.
    area : str
        Area name.
    
    Returns
    -------
    tuple of (list of str, pandas.DataFrame)
        (findings, table).
    """
    series = data.get_purchasing_power(end=month, area=area).tail(13)  # Last 13 months
    now, then = series["value"].iloc[-1], series["value"].iloc[0]     # Current and 12 months ago
    fies = data.get_fies_by_decile(area if area in data.list_areas("region") else data.NATIONAL)
    groups = fies[fies["decile"] != "All Income Groups"]
    findings = [f"Purchasing power of the peso was {now:.2f} in {month_label(month)}, {now - then:+.2f} over the past 12 months.",
                f"FIES 2023: the bottom 10% of earners saved {groups.iloc[0]['savings_rate']:.1f}% of income and the top "
                f"10% {groups.iloc[-1]['savings_rate']:.1f}%. FIES is a 2023 snapshot, not a trend."]
    table = fies.assign(decile=fies["decile"].map(tokens.DECILE_SHORT))[["decile", "income", "expenditure", "savings", "savings_rate"]]
    table.columns = ["Income level", "Income (thousand pesos)", "Expenditure (thousand pesos)", "Savings (thousand pesos)", "Savings rate (%)"]
    return findings, table


def regional_comparison(month, area):
    """Build a regional comparison report for one month.
    
    Parameters
    ----------
    month : pandas.Timestamp
        The report month.
    area : str
        Area name (unused; report covers all regions).
    
    Returns
    -------
    tuple of (list of str, pandas.DataFrame)
        (findings, table).
    """
    frames = [data.get_regional_comparison(ind, month).set_index("region")["value"].rename(theme.INDICATOR_SHORT_NAMES[ind])
              for ind in data.INDICATORS]
    table = pd.concat(frames, axis=1).sort_values("CPI", ascending=False).reset_index(names="Region")
    findings = [f"Highest CPI: {table.iloc[0]['Region']} ({table.iloc[0]['CPI']:.1f}); lowest: {table.iloc[-1]['Region']} ({table.iloc[-1]['CPI']:.1f}).",
                f"Highest inflation: {table.sort_values('Inflation').iloc[-1]['Region']} ({table['Inflation'].max():.1f}%)."]
    return findings, table


def forecast_results(month, area):
    """Build a CPI forecast and model results report.
    
    Parameters
    ----------
    month : pandas.Timestamp
        The report month (unused; report covers the next 12 months).
    area : str
        Area name (unused; report covers national).
    
    Returns
    -------
    tuple of (list of str, pandas.DataFrame)
        (findings, table).
    """
    info = data.get_model_info()
    frames = [data.get_forecast(v, 12).set_index("date")["forecast"].rename(theme.INDICATOR_SHORT_NAMES[v]) for v in data.INDICATORS]
    table = pd.concat(frames, axis=1).reset_index(names="Month")
    table["Month"] = table["Month"].dt.strftime("%b %Y")
    metrics = data.get_model_metrics("cpi").set_index("model").loc[info["final_model"]]
    findings = [f"Selected model: {info['final_model']} (lowest overall error across six evaluation periods).",
                f"Next-month CPI forecast: {table.iloc[0]['CPI']:.1f}; 12 months ahead: {table.iloc[-1]['CPI']:.1f}.",
                f"CPI forecast error, all evaluation periods: MAE {metrics['mae']:.2f}, RMSE {metrics['rmse']:.2f}, MAPE {metrics['mape']:.2f}%.",
                tokens.FORECAST_DISCLAIMER]
    return findings, table


# Map report type names to their builder functions.
BUILDERS = {"Cost-of-Living Summary": cost_of_living_summary, "Commodity Price Trends": commodity_trends,
            "Household Purchasing Power": household_purchasing_power, "Regional Comparison": regional_comparison,
            "CPI Forecast and Model Results": forecast_results}


def build_report(kind, month, area):
    """Build a full report (findings + table + Markdown) for one report type.
    
    Parameters
    ----------
    kind : str
        Report type (must be a key in BUILDERS).
    month : pandas.Timestamp
        The report month.
    area : str
        Area name.
    
    Returns
    -------
    dict
        Report record with id, kind, coverage, scope, generated, findings,
        table, and markdown.
    """
    findings, table = BUILDERS[kind](month, area)
    coverage = "Next 12 months" if kind == REPORT_TYPES[4] else month_label(month)
    scope = "All regions" if kind in (REPORT_TYPES[3], REPORT_TYPES[4]) else area_label(area)
    now = datetime.now()
    markdown = (f"# PresyoPH: {kind}\n\nCoverage: {coverage}  \nRegion: {scope}  \nGenerated: {now:%b %d, %Y %H:%M}\n\n"
                "## Key findings\n" + "\n".join(f"- {f}" for f in findings) + "\n\n## Data\n" + _md_table(table) +
                f"\n\n{tokens.PSA_ATTRIBUTION}\n")
    return {"id": now.strftime("%Y%m%d%H%M%S%f"), "kind": kind, "coverage": coverage, "scope": scope,
            "generated": now, "findings": findings, "table": table, "markdown": markdown}


def render():
    """Render the Reports page."""
    shell.page_header("Reports", "Generate and download PresyoPH analytics reports from the latest PSA data.",
                      shell.pill("Built from the same data as the dashboard", dot=True))
    reports = st.session_state.setdefault("reports", [])  # Store generated reports in session state

    with st.container(key="filter_reports"):              # Report generation controls
        st.markdown("**Generate a New Report**  \nChoose the report scope and coverage below.")
        c1, c2, c3, c4 = st.columns([1.6, 1.3, 1.6, 1.0], vertical_alignment="bottom")
        kind = c1.selectbox("Report Type", REPORT_TYPES, key="rep_kind")
        months = month_options("inflation")[1:]           # Skip first month (inflation starts Jan 2019)
        month = c2.selectbox("Date Period", list(reversed(months)), format_func=month_label, key="rep_month")
        needs_area = kind in REPORT_TYPES[:3]             # First 3 report types need an area
        area = c3.selectbox("Region", area_options(), format_func=area_label, key="rep_area", disabled=not needs_area)
        generate = c4.button("Generate Report", type="primary", use_container_width=True)
    if generate:
        with st.spinner("Building report…"):
            try:
                reports.insert(0, build_report(kind, month, area if needs_area else data.NATIONAL))
                st.session_state["rep_selected"] = reports[0]["id"]
                st.toast("Report generated.", icon=":material/check_circle:")
            except ValueError as err:
                st.error(f"Could not build this report: {err}")

    # Left column: list of recent reports; Right column: report details
    left, right = st.columns([2.2, 1])
    with left:
        with st.container(key="card_reports_list"):
            shell.panel_header("Recent Reports", "Reports generated in this session", right=f"{len(reports)} reports")
            if not reports:
                st.info("No reports yet. Choose a report type above and select Generate Report.", icon=":material/description:")
            for r in reports:
                c = st.columns([2.4, 1.2, 1.3, 0.8, 0.8], vertical_alignment="center")
                c[0].markdown(f"**{r['kind']}**  \n<small>{shell.esc(r['scope'])}</small>", unsafe_allow_html=True)
                c[1].markdown(f"<small>{r['generated']:%b %d, %Y}</small>", unsafe_allow_html=True)
                c[2].markdown(f"<small>{shell.esc(r['coverage'])}</small>", unsafe_allow_html=True)
                if c[3].button("View", key=f"view_{r['id']}"):
                    st.session_state["rep_selected"] = r["id"]
                c[4].download_button("Download", r["markdown"], file_name=f"presyoph_{r['id']}.md", mime="text/markdown",
                                     key=f"dl_{r['id']}", type="primary")
    with right:
        with st.container(key="card_report_detail"):
            shell.panel_header("Report Details")
            chosen = next((r for r in reports if r["id"] == st.session_state.get("rep_selected")), None)
            if chosen is None:
                st.caption("Select View beside a recent report to see its details.")
            else:
                st.markdown(f"**{chosen['kind']}**  \n{chosen['coverage']} · {chosen['scope']}")
                for f in chosen["findings"]:
                    st.markdown(f"- {f}")
                st.download_button("Download data (CSV)", chosen["table"].to_csv(index=False), file_name=f"presyoph_{chosen['id']}.csv",
                                   mime="text/csv", key=f"csv_{chosen['id']}")
    chosen = next((r for r in reports if r["id"] == st.session_state.get("rep_selected")), None)
    if chosen is not None:
        with st.container(key="card_report_table"):
            shell.panel_header(chosen["kind"], f"{chosen['coverage']} · {chosen['scope']}", right="Data")
            st.dataframe(chosen["table"], hide_index=True)


render()                                               # Execute the page when Streamlit loads it
