"""Screen 5: Regional Comparison (Figma: Regional Cost-of-Living Comparison)."""

import streamlit as st

from app import theme
from app.ui import charts, queries, shell
from app.ui.layout import month_label, month_options
from backend import data

INDICATOR_CHOICES = ["cpi", "inflation", "purchasing_power"]
NAMES = {"cpi": "Consumer Price Index (CPI)", "inflation": "Inflation rate", "purchasing_power": "Purchasing power of the peso"}


def short(region):
    """'Region IV-A (CALABARZON)' -> 'CALABARZON'; keeps the region code as a sub label."""
    if "(" in region:
        return region[region.index("(") + 1:region.rindex(")")], region[:region.index("(")].strip()
    return region, ""


def ranking_card(ranking, indicator, selected, suffix):
    ranking = ranking.reset_index(drop=True)
    top = ranking["value"].max()
    rows = []
    for i, r in ranking.iterrows():
        name, code = short(r["region"])
        bold = "font-weight:800" if r["region"] == selected else ""
        bg = "background:#eaf2e6;" if r["region"] == selected else ""
        rows.append(f'<tr style="{bg}"><td style="width:22px;color:#6b7f78;font-size:11px">{r["rank"]}</td>'
                    f'<td style="width:36%;font-size:12px;{bold}">{shell.esc(name)}<small>{shell.esc(code)}</small></td>'
                    f'<td><div class="pp-bar" style="height:10px"><i style="width:{r["value"] / top * 100:.1f}%;'
                    f'background:{shell.rank_color(i, len(ranking), indicator == "purchasing_power")}"></i></div></td>'
                    f'<td class="num" style="width:56px;font-weight:700">{r["value"]:.{2 if indicator == "purchasing_power" else 1}f}{suffix}</td></tr>')
    st.markdown(f'<table class="pp-tbl">{"".join(rows)}</table>', unsafe_allow_html=True)
    shell.rank_legend(indicator == "purchasing_power")


def table_card(ranking, indicator, selected, suffix):
    national = ranking.attrs["national"]
    rows = []
    for _, r in ranking.iterrows():
        name, code = short(r["region"])
        diff = r["difference_from_national"]
        pct = diff / national * 100 if national else 0
        good = diff >= 0 if indicator == "purchasing_power" else diff < 0  # higher cost is worse, higher buying power is better
        cls, arrow = ("up" if good else "dn"), ("▲" if diff >= 0 else "▼")
        gap = f"{abs(diff):.1f} pts" if indicator == "inflation" else f"{abs(pct):.1f}%"
        sel = ' class="sel"' if r["region"] == selected else ""
        rows.append(f'<tr{sel}><td>{r["rank"]}</td><td>{shell.esc(name)}<small>{shell.esc(queries.region_group_of(r["region"]))}</small></td>'
                    f'<td class="num">{r["value"]:.{2 if indicator == "purchasing_power" else 1}f}{suffix}</td>'
                    f'<td class="num {cls}">{arrow} {gap}</td></tr>')
    st.markdown('<table class="pp-tbl"><tr><th>Rank</th><th>Region</th><th class="num">'
                f'{shell.esc(theme.INDICATOR_SHORT_NAMES[indicator])}</th><th class="num">vs. Nat\'l</th></tr>{"".join(rows)}</table>',
                unsafe_allow_html=True)


def render():
    last = data.get_date_range("cpi")[1]
    shell.page_header("Regional Cost-of-Living Comparison",
                      "Compare price levels, inflation, and household purchasing power across Philippine regions.",
                      shell.chip(month_label(last), icon="calendar", boxed=True, sub="Latest available period"))

    groups = queries.list_region_groups()
    if st.session_state.get("reg_group") not in groups:
        st.session_state["reg_group"] = groups[0]
    with st.container(key="filter_reg"):
        c1, c2, c3, c4, c5 = st.columns([1.5, 1.1, 1.5, 1.0, 1.7], vertical_alignment="center")
        indicator = c1.selectbox("Indicator", INDICATOR_CHOICES, format_func=NAMES.get, key="reg_indicator")
        group = c2.selectbox("Region Group", groups, key="reg_group")
        region_options = queries.regions_in_group(group)
        if st.session_state.get("reg_region") not in region_options:
            st.session_state["reg_region"] = region_options[0]
        selected = c3.selectbox("Selected Region", region_options, key="reg_region")
        months = month_options(indicator)
        month = c4.selectbox("Month", list(reversed(months)), format_func=month_label, key="reg_month")
        categories = data.list_categories(include_all_items=True)
        item = data.ALL_ITEMS
        if indicator != "purchasing_power":
            label = st.selectbox("Category", list(categories["label"]), key="reg_category")
            item = categories.set_index("label").loc[label, "item"]
        else:
            st.caption("Purchasing power is published for all items only, so there is no category filter.")

    ranking = data.get_regional_comparison(indicator, month, item, region_options)
    suffix = "%" if indicator == "inflation" else ""
    value = ranking.loc[ranking["region"] == selected, "value"]
    fmt = ".2f" if indicator == "purchasing_power" else ".1f"
    with c5:
        shell.filter_stat(f"Selected Region: {short(selected)[0]}", f"{value.iloc[0]:{fmt}}{suffix}",
                          f"Philippines: {ranking.attrs['national']:{fmt}}{suffix}")

    if ranking["value"].round(2).duplicated(keep=False).any():
        st.caption("Regions with the same published value are tied; their order here is not meaningful.")

    left, right = st.columns([1.15, 1])
    with left:
        with st.container(key="card_reg_rank"):
            shell.panel_header(f"Regional Ranking: {NAMES[indicator]}", f"Regional comparison for {group.lower()}, {month_label(month)}",
                               right="Highest to lowest", icon="trend")
            ranking_card(ranking, indicator, selected, suffix)
    with right:
        with st.container(key="card_reg_table"):
            shell.panel_header("Regional Comparison Table", "Detailed values and variance from the national figure",
                               right=f"{len(ranking)} regions", icon="file")
            table_card(ranking, indicator, selected, suffix)
    with st.expander("Notes on regions and indicators"):
        st.markdown(
            "- Regions follow PSA's current list of 18 regions. Inflation starts in January 2019; CPI and purchasing power in January 2018.\n"
            "- Purchasing power is published for all items only, not by category.\n"
            "- Household income, spending, and savings by region (2023) are on the Purchasing Power page.")


render()
