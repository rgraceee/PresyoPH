"""The PresyoPH app shell and shared UI pieces, built from the Figma design:
sidebar, top bar with working search, page headers, KPI cards, insight cards.

Optional brand artwork exported from Figma goes in app/assets/:
  logo.svg (or .png)           the PresyoPH mark above the wordmark
  sidebar_illustration.svg     the house-and-leaf artwork at the bottom of the sidebar
If a file is missing the sidebar falls back to the text wordmark and tagline.
"""

import base64
import html
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from app.ui import queries, tokens
from app.ui.layout import month_label
from backend import data

APP_DIR = Path(__file__).resolve().parent
ASSETS = APP_DIR / "assets"
STATIC = APP_DIR / "static"

# key, sidebar label, icon. The first six follow the Figma sidebar; the rest are the system's other screens
# (Forecast Details is the existing Forecasts page by Member 2, kept as is).
NAV = [
    ("home", "Dashboard", ":material/home:"),
    ("trends", "Price Trends", ":material/trending_up:"),
    ("categories", "Household Necessities", ":material/shopping_basket:"),
    ("finances", "Purchasing Power", ":material/account_balance_wallet:"),
    ("regional", "Household Analysis", ":material/groups:"),
    ("forecasting", "Forecasting", ":material/calendar_month:"),
    ("reports", "Reports", ":material/description:"),
    ("explorer", "Data Explorer", ":material/table_chart:"),
    ("about", "About / Methodology", ":material/info:"),
]
NAV_DIVIDER_BEFORE = "explorer"  # the Figma sidebar ends at Reports; the system's extra screens follow a divider
SEARCH_KEY = "global_search"
_SVG = ('<svg class="pp-ico" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{}</svg>')
ICONS = {
    "chart": _SVG.format('<path d="M3 3v18h18"/><path d="M8 17v-5"/><path d="M13 17V7"/><path d="M18 17v-8"/>'),
    "trend": _SVG.format('<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>'),
    "pin": _SVG.format('<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>'),
    "wallet": _SVG.format('<path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/>'
                          '<path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/>'),
    "house": _SVG.format('<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/>'
                         '<path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'),
    "bulb": _SVG.format('<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/>'
                        '<path d="M9 18h6"/><path d="M10 22h4"/>'),
    "file": _SVG.format('<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
                        '<path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>'),
    "calendar": _SVG.format('<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>'),
    "users": _SVG.format('<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'),
    "info": _SVG.format('<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>'),
}
ICON_CHART = ICONS["chart"]


def greeting():
    """Time-of-day greeting in Philippine time (the app has no user accounts, so no name)."""
    hour = datetime.now(ZoneInfo("Asia/Manila")).hour
    return "Good morning!" if hour < 12 else "Good afternoon!" if hour < 18 else "Good evening!"


# --- helpers ---------------------------------------------------------------------------------

def esc(text):
    return html.escape(str(text), quote=True)


def _asset_uri(*names):
    for name in names:
        path = ASSETS / name
        if path.exists():
            mime = {"svg": "image/svg+xml", "png": "image/png"}.get(path.suffix.lstrip("."), "application/octet-stream")
            return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"
    return None


def md(markup):
    st.markdown(markup, unsafe_allow_html=True)


def inject_css():
    st.markdown(f"<style>{(STATIC / 'presyoph.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


# --- sidebar and top bar -----------------------------------------------------------------------

def sidebar(pages):
    logo = _asset_uri("logo.svg", "logo.png")
    art = _asset_uri("sidebar_illustration.svg", "sidebar_illustration.png")
    with st.sidebar:
        md(f'<div class="pp-brand">{f"<img src={chr(34)}{logo}{chr(34)} alt={chr(34)}{chr(34)}>" if logo else ""}'
           '<div class="pp-word">PRESYOPH</div>'
           '<div class="pp-tag">Understanding Prices.<br>Measuring Purchasing Power.</div></div>'
           '<div class="pp-nav-gap"></div>')
        for key, label, icon in NAV:
            if key == NAV_DIVIDER_BEFORE:
                md('<div class="pp-nav-sep"></div>')
            st.page_link(
                pages[key],
                label=label,
                icon=icon,
)
        md(f'<div class="pp-side-foot">{f"<img src={chr(34)}{art}{chr(34)} alt={chr(34)}{chr(34)}>" if art else ""}'
           '<div class="pp-script">Better Data.<br>Smarter Decisions.<br>Stronger Households.</div></div>')


def _go(target, state):
    st.session_state.update(state)
    st.session_state["_goto"] = target
    st.session_state[SEARCH_KEY] = ""


def _matches(query):
    found = [(f"Page: {label}", key, {}) for key, label, _ in NAV if query in label.lower()]
    for label in data.list_categories()["label"]:
        if query in label.lower():
            found.append((f"Category: {label}", "categories", {"cat_select": label}))
    for region in data.list_areas("region"):
        if query in region.lower():
            found.append((f"Region: {region}", "regional",
                          {"reg_group": queries.region_group_of(region), "reg_region": region}))
    return found[:7]


def _notices():
    """What the bell shows: real facts about the data and the forecast, computed from the backend."""
    last = data.get_date_range("cpi")[1]
    latest = data.get_latest()
    top = data.get_top_category()
    info = data.get_model_info()
    return [
        ("Data updated", f"PSA figures run through {month_label(last)}."),
        ("Prices", f"CPI is {latest['cpi']['value']:.1f} ({latest['cpi']['change']:+.1f} from last month); "
                   f"inflation is {latest['inflation']['value']:.1f}%."),
        ("Biggest category rise", f"{top['label']} has the highest inflation at {top['inflation']:.1f}%."),
        ("Forecast", f"{info['final_model']} forecast uses data through {info['data']['end']}."),
    ]


def topbar(pages):
    """Search box (pages, categories, regions), data date, notices and the profile menu, as in the Figma header."""
    target = st.session_state.pop("_goto", None)
    if target:
        st.switch_page(pages[target])
    last = data.get_date_range("cpi")[1]
    today = datetime.now(ZoneInfo("Asia/Manila"))
    with st.container(key="topbar"):
        search, date, bell, profile = st.columns([4.4, 2.1, 0.65, 1.0], vertical_alignment="center")
        query = search.text_input("Search", key=SEARCH_KEY, label_visibility="collapsed",
                                  placeholder="Search for a region, category, or page…")
        date.markdown(f'<div class="pp-date">{ICONS["calendar"]}<div><b>{today:%B} {today.day}, {today.year}</b>'
                      f'<span>Data through {month_label(last)}</span></div></div>', unsafe_allow_html=True)
        
        
        
        with bell:
            with st.container(key="bell"):
                with st.popover(
                    "Notices",
                    icon=":material/notifications:",
                    help="Data and forecast notices",
                ):
                    st.markdown(
                        "".join(
                            f'<div class="pp-notice"><b>{esc(h)}</b>{esc(b)}</div>'
                            for h, b in _notices()
                        ),
                        unsafe_allow_html=True,
                    )

        with profile:
            with st.container(key="profile"):
                with st.popover(
                    "Guest",
                    icon=":material/account_circle:",
                ):
                    st.markdown(
                        '<div class="pp-notice"><b>Guest view</b>'
                        'PresyoPH uses public PSA statistics, so no sign-in is needed.</div>',
                        unsafe_allow_html=True,
                    )
                    st.page_link(
                        pages["about"],
                        label="About / Methodology",
                        icon=":material/info:",
                    )
                    st.page_link(
                        pages["explorer"],
                        label="Data Explorer",
                        icon=":material/table_chart:",
                    )

    query = (query or "").strip().lower()
    if query:
        results = _matches(query)
        with st.container(key="search_results"):
            if not results:
                st.caption("No matching page, category, or region.")
            for i, (label, key, state) in enumerate(results):
                st.button(label, key=f"sr_{i}", on_click=_go, args=(key, state), use_container_width=True)


# --- page furniture -----------------------------------------------------------------------------

def page_header(title, subtitle, right_html=""):
    md(f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap">'
       f'<div><div class="pp-h1">{esc(title)}</div><div class="pp-sub">{esc(subtitle)}</div></div>'
       f'<div style="padding-top:.5rem">{right_html}</div></div>')


def chip(text, icon=None, boxed=False, sub=None):
    """Small status note at the right of a page title (Figma: 'Updated October 2025', 'Latest available period')."""
    glyph = ICONS[icon] if icon else '<i class="pp-dot"></i>'
    body = f'<span>{esc(text)}</span>' if not sub else f'<span><b>{esc(text)}</b><br>{esc(sub)}</span>'
    return f'<span class="pp-chip{" pp-chip-box" if boxed else ""}">{glyph}{body}</span>'


def filter_title(title, subtitle, icon="trend"):
    md(f'<div class="pp-fhead"><span class="pp-fic">{ICONS[icon]}</span><div><b>{esc(title)}</b><span>{esc(subtitle)}</span></div></div>')



def filter_stat(label, value, sub="", tone=""):
    """Selected-value summary at the right of a filter bar."""
    md(
        f'<div class="pp-fstat">'
        f'<div class="pp-fl">'
        f'<b>{esc(label)}</b>'
        f'<span class="pp-fsub">{esc(sub)}</span>'
        f'</div>'
        f'<div class="pp-fv {esc(tone)}">{esc(value)}</div>'
        f'</div>'
    )


def pill(text, tone="", dot=False):
    return f'<span class="pp-pill {tone}">{"<i class=pp-dot></i>" if dot else ""}{esc(text)}</span>'


def panel_header(title, subtitle=None, right=None, icon="chart"):
    icon = ICONS.get(icon, icon)
    md(f'<div class="pp-ph">{icon}<div><h3>{esc(title)}</h3>{f"<p>{esc(subtitle)}</p>" if subtitle else ""}</div>'
       f'{f"<div class=pp-right>{esc(right)}</div>" if right else ""}</div>')


def kpi_card(label, value, badge, delta=None, bad=None, tone="green", foot="vs. last month", help=None):
    """Summary card. `bad` colours the change: True red, False green, None grey."""
    cls = {True: "bad", False: "good", None: "flat"}[bad]
    delta_html = f'<span class="pp-d {cls}">{esc(delta)}</span>' if delta else ""
    info = f'<span class="pp-info" title="{esc(help)}">i</span>' if help else ""
    md(f'<div class="pp-kpi {tone}"><div class="pp-badge">{esc(badge)}</div><div class="pp-lab">{esc(label)}{info}</div>'
       f'<div class="pp-val">{esc(value)}{delta_html}</div><div class="pp-foot">{esc(foot)}</div></div>')


def mini_card(label, value, top_right="", bottom_right="", tone="green"):
    md(f'<div class="pp-mini {tone}"><div class="pp-ml">{esc(label)}</div><div class="pp-row"><div class="pp-mv">{esc(value)}</div>'
       f'<div style="text-align:right"><div class="pp-ms" style="font-weight:700">{esc(top_right)}</div>'
       f'<div class="pp-ms">{esc(bottom_right)}</div></div></div></div>')


def insight_card(title, items, icon="bulb"):
    """items: list of (heading, body) pairs. Content must be computed from data by the caller."""
    icon = ICONS.get(icon, esc(icon))
    rows = "".join(f"<li>{f'<b>{esc(h)}</b>' if h else ''}{esc(b)}</li>" for h, b in items)
    md(f'<div class="pp-insight"><h4><span class="pp-ih">{icon}</span>{esc(title)}</h4><ul>{rows}</ul></div>')


def ranked_list(rows):
    """rows: dicts with rank, name, sub, change (percent, float)."""
    items = []
    for r in rows:
        neg = " neg" if r["change"] < 0 else ""
        items.append(f'<div class="pp-li"><span class="pp-rk">{r["rank"]}</span>'
                     f'<span class="pp-circ">{esc(r["name"][:1])}</span>'
                     f'<span class="pp-nm">{esc(r["name"])}<small>{esc(r.get("sub", ""))}</small></span>'
                     f'<span class="pp-ch{neg}">{r["change"]:+.1f}%</span></div>')
    md(f'<div class="pp-list">{"".join(items)}</div>')


def rank_color(i, n, higher_is_better):
    """Colour for the i-th row (0 = highest value) of n ranked rows. For cost indicators (CPI, inflation) a
    higher value is worse, so the highest is warm; for purchasing power the highest is good."""
    palette = tokens.RANK_COLORS if higher_is_better else tokens.RANK_COLORS[::-1]
    return palette[min(len(palette) - 1, int(i * len(palette) / max(n, 1)))]


def rank_legend(higher_is_better):
    top, mid, low = (tokens.RANK_COLORS[0], tokens.RANK_COLORS[2], tokens.RANK_COLORS[4])
    if not higher_is_better:
        top, low = low, top
    names = ("Higher value", "Mid-range", "Lower value")
    md('<div class="pp-legend">' + "".join(f'<span><i style="background:{c}"></i>{n}</span>'
                                          for c, n in zip((top, mid, low), names)) + '</div>')


def quote_card(text="Informed households build a more resilient Philippine economy."):
    md(f'<div class="pp-quote">{esc(text)}<i></i></div>')


def footer():
    md(f'<div class="pp-foot-note">{esc(tokens.PSA_ATTRIBUTION)}<br><b>Forecast disclaimer:</b> '
       f'{esc(tokens.FORECAST_DISCLAIMER)}</div>')

