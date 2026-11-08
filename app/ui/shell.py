"""
================================================================================
FILE: app/ui/shell.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
This file contains the shared UI "shell" for the PresyoPH dashboard. It builds
the common visual elements that appear on every page:

  - Sidebar (logo, navigation links, brand artwork)
  - Top bar (search box, current date, data freshness, notices bell, profile)
  - Page headers (title, subtitle, right-side HTML)
  - KPI cards (summary numbers with deltas)
  - Insight cards (bulleted insights)
  - Ranked lists, bars, chips, pills, legends
  - Footer (PSA attribution and forecast disclaimer)

All functions here return HTML strings or call Streamlit directly. They are
called by every page in app/pages/.

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- app/streamlit_app.py: Calls shell.inject_css(), shell.sidebar(), shell.topbar(),
  shell.footer() to build the app shell.
- app/pages/*.py: Call shell.page_header(), shell.kpi_card(), shell.insight_card(),
  shell.panel_header(), shell.filter_title(), etc. to build each page's UI.
- app/ui/queries.py: shell._matches() calls queries.region_group_of() for search.
- app/ui/tokens.py: shell uses tokens.RANK_COLORS, tokens.PSA_ATTRIBUTION,
  tokens.FORECAST_DISCLAIMER.
- backend/data.py: shell._notices() calls data.get_date_range(), data.get_latest(),
  data.get_top_category(), data.get_model_info().

================================================================================
"""

"""The PresyoPH app shell and shared UI pieces, built from the Figma design:
sidebar, top bar with working search, page headers, KPI cards, insight cards.

Optional brand artwork exported from Figma goes in app/assets/:
  logo.svg (or .png)           the PresyoPH mark above the wordmark
  sidebar_illustration.svg     the house-and-leaf artwork at the bottom of the sidebar
If a file is missing the sidebar falls back to the text wordmark and tagline.
"""

import base64                                          # base64: encodes image files as data URIs for HTML
import html                                            # html: escapes text to prevent HTML injection attacks
from datetime import datetime                          # datetime: gets current date/time for greeting and top bar
from pathlib import Path                               # Path: works with file system paths (assets, static)
from zoneinfo import ZoneInfo                          # ZoneInfo: timezone support (Asia/Manila for Philippine time)

import streamlit as st                                 # streamlit: the web framework that runs the dashboard

from app.ui import queries, tokens                     # queries: extra data helpers; tokens: Figma colours and wording
from app.ui.layout import month_label                  # month_label: formats a date as "Aug 2026"
from backend import data                               # backend data access layer (gets latest data, categories, regions, etc.)

APP_DIR = Path(__file__).resolve().parent             # Directory containing this file (app/ui/)
ASSETS = APP_DIR / "assets"                           # Path to app/ui/assets/ (logo images, sidebar illustration)
STATIC = APP_DIR / "static"                           # Path to app/ui/static/ (CSS file)

# Navigation menu items. Each tuple is: (page_key, display_label, material_icon_name).
# The page_key matches keys in the PAGES dict in streamlit_app.py.
# These are used to render sidebar links and search results.
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
NAV_DIVIDER_BEFORE = "explorer"  # Insert a visual divider before "Data Explorer" in the sidebar
SEARCH_KEY = "global_search"     # Session state key for the search box text

# SVG icon template: creates an 18x18 SVG icon with the given path data.
# Used for custom icons in chips, panel headers, etc. (not Material icons).
_SVG = ('<svg class="pp-ico" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{}</svg>')

# Dictionary of custom SVG icons keyed by name. Each value is an SVG string.
# These are used in panel_header(), chip(), filter_title(), etc.
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
ICON_CHART = ICONS["chart"]  # Shortcut to the chart icon


def greeting():
    """Return a time-of-day greeting in Philippine time.
    
    The app has no user accounts, so there's no personal name to show.
    Returns "Good morning!", "Good afternoon!", or "Good evening!".
    
    Returns
    -------
    str
        Greeting string.
    """
    hour = datetime.now(ZoneInfo("Asia/Manila")).hour  # Get current hour in Philippine time (UTC+8)
    return "Good morning!" if hour < 12 else "Good afternoon!" if hour < 18 else "Good evening!"


# --- Helper functions ---------------------------------------------------------
# These are small utilities used by the larger UI functions.

def esc(text):
    """Escape text for safe HTML output (prevents XSS/injection attacks).
    
    Parameters
    ----------
    text : any
        Text to escape.
    
    Returns
    -------
    str
        HTML-escaped text.
    """
    return html.escape(str(text), quote=True)  # Convert special chars to HTML entities (&, <, >, ", ')


def _asset_uri(*names):
    """Find an asset file and return it as a base64 data URI.
    
    Tries each filename in order. Returns the first one that exists.
    Used for logo and sidebar illustration images.
    
    Parameters
    ----------
    *names : str
        Filenames to try (e.g. "logo.svg", "logo.png").
    
    Returns
    -------
    str or None
        Data URI like "data:image/svg+xml;base64,..." or None if no file found.
    """
    for name in names:                                   # Try each filename
        path = ASSETS / name                             # Full path to the asset
        if path.exists():                                # If the file exists
            mime = {"svg": "image/svg+xml", "png": "image/png"}.get(path.suffix.lstrip("."), "application/octet-stream")
            # Determine MIME type from file extension
            return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"  # Encode as base64 data URI
    return None                                          # No asset file found


def md(markup):
    """Render HTML markup as Streamlit markdown.
    
    Parameters
    ----------
    markup : str
        HTML string to render.
    """
    st.markdown(markup, unsafe_allow_html=True)          # Allow HTML in Streamlit markdown


def inject_css():
    """Inject the custom CSS file (presyoph.css) into the Streamlit app.
    
    This applies the PresyoPH visual styling (colours, fonts, layout classes)
    to all pages.
    """
    st.markdown(f"<style>{(STATIC / 'presyoph.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    # Read the CSS file and inject it as a <style> block


# --- Sidebar and top bar -------------------------------------------------------

def sidebar(pages):
    """Render the left sidebar with logo, navigation, and brand artwork.
    
    Parameters
    ----------
    pages : dict
        Dict of page_key -> st.Page objects (from streamlit_app.py).
    """
    logo = _asset_uri("logo.svg", "logo.png")            # Try to find logo image (svg or png)
    art = _asset_uri("sidebar_illustration.svg", "sidebar_illustration.png")  # Try to find sidebar illustration
    with st.sidebar:                                     # All Streamlit calls here go in the sidebar
        # Brand section: logo image (or blank), wordmark "PRESYOPH", tagline
        md(f'<div class="pp-brand">{f"<img src={chr(34)}{logo}{chr(34)} alt={chr(34)}{chr(34)}>" if logo else ""}'
           '<div class="pp-word">PRESYOPH</div>'
           '<div class="pp-tag">Understanding Prices.<br>Measuring Purchasing Power.</div></div>'
           '<div class="pp-nav-gap"></div>')
        # Navigation links: one st.page_link per NAV item
        for key, label, icon in NAV:
            if key == NAV_DIVIDER_BEFORE:                # Insert a visual divider before "explorer"
                md('<div class="pp-nav-sep"></div>')
            st.page_link(                              # Streamlit navigation link
                pages[key],                            # Target page
                label=label,                           # Display text
                icon=icon,                             # Material icon
            )
        # Sidebar footer: brand illustration image (or blank)
        md(f'<div class="pp-side-foot">{f"<img src={chr(34)}{art}{chr(34)} alt={chr(34)}{chr(34)}>" if art else ""}'
           '</div>')


def _go(target, state):
    """Handle search result clicks: update session state and navigate to a page.
    
    Parameters
    ----------
    target : str
        Page key to navigate to.
    state : dict
        Session state variables to set before navigating.
    """
    st.session_state.update(state)                       # Set any state variables (e.g. selected category)
    st.session_state["_goto"] = target                   # Flag to switch pages on next rerun
    st.session_state[SEARCH_KEY] = ""                    # Clear the search box


def _matches(query):
    """Search for pages, categories, and regions matching the query.
    
    Parameters
    ----------
    query : str
        Search text (lowercase).
    
    Returns
    -------
    list of tuples
        Each tuple is (display_label, page_key, state_dict). Max 7 results.
    """
    found = [(f"Page: {label}", key, {}) for key, label, _ in NAV if query in label.lower()]  # Match page labels
    for label in data.list_categories()["label"]:        # Match commodity group names
        if query in label.lower():
            found.append((f"Category: {label}", "categories", {"cat_select": label}))
    for region in data.list_areas("region"):             # Match region names
        if query in region.lower():
            found.append((f"Region: {region}", "regional",
                          {"reg_group": queries.region_group_of(region), "reg_region": region}))
    return found[:7]                                     # Limit to 7 results


def _notices():
    """Build the notices shown in the top bar bell popover.
    
    Returns
    -------
    list of tuples
        Each tuple is (heading, body_text).
    """
    last = data.get_date_range("cpi")[1]                  # Latest date with CPI data
    latest = data.get_latest()                            # Latest values for all indicators
    top = data.get_top_category()                         # Category with highest inflation
    info = data.get_model_info()                          # Model info (which model is selected)
    return [
        ("Data updated", f"PSA figures run through {month_label(last)}."),  # Data freshness notice
        ("Prices", f"CPI is {latest['cpi']['value']:.1f} ({latest['cpi']['change']:+.1f} from last month); "
                   f"inflation is {latest['inflation']['value']:.1f}%."),  # Latest prices notice
        ("Biggest category rise", f"{top['label']} has the highest inflation at {top['inflation']:.1f}%."),  # Top category notice
        ("Forecast", f"{info['final_model']} forecast uses data through {info['data']['end']}."),  # Forecast model notice
    ]


def topbar(pages):
    """Render the top header bar: search, date, notices bell, profile menu.
    
    Also handles search box input and navigation from search results.
    
    Parameters
    ----------
    pages : dict
        Dict of page_key -> st.Page objects.
    """
    target = st.session_state.pop("_goto", None)         # Check if we need to navigate (from search click)
    if target:
        st.switch_page(pages[target])                    # Switch to the target page
    last = data.get_date_range("cpi")[1]                  # Latest data date
    today = datetime.now(ZoneInfo("Asia/Manila"))        # Current date/time in Philippine time
    with st.container(key="topbar"):                      # Container for the top bar layout
        search, date, bell, profile = st.columns([4.4, 2.1, 0.65, 1.0], vertical_alignment="center")
        # Search input field
        query = search.text_input("Search", key=SEARCH_KEY, label_visibility="collapsed",
                                  placeholder="Search for a region, category, or page…")
        # Date display showing today's date and data freshness
        date.markdown(f'<div class="pp-date">{ICONS["calendar"]}<div><b>{today:%B} {today.day}, {today.year}</b>'
                      f'<span>Data through {month_label(last)}</span></div></div>', unsafe_allow_html=True)

        # Notifications bell popover
        with bell:
            with st.container(key="bell"):
                with st.popover("Notices", icon=":material/notifications:", help="Data and forecast notices"):
                    st.markdown(
                        "".join(
                            f'<div class="pp-notice"><b>{esc(h)}</b>{esc(b)}</div>'  # Each notice as heading + body
                            for h, b in _notices()
                        ),
                        unsafe_allow_html=True,
                    )

        # Profile/guest popover with links to About and Data Explorer
        with profile:
            with st.container(key="profile"):
                with st.popover("Guest", icon=":material/account_circle:"):
                    st.markdown(
                        '<div class="pp-notice"><b>Guest view</b>'
                        'PresyoPH uses public PSA statistics, so no sign-in is needed.</div>',
                        unsafe_allow_html=True,
                    )
                    st.page_link(pages["about"], label="About / Methodology", icon=":material/info:")
                    st.page_link(pages["explorer"], label="Data Explorer", icon=":material/table_chart:")

    # Handle search box: if user typed something, show matching results
    query = (query or "").strip().lower()
    if query:
        results = _matches(query)                          # Find matching pages/categories/regions
        with st.container(key="search_results"):
            if not results:
                st.caption("No matching page, category, or region.")
            for i, (label, key, state) in enumerate(results):  # Show each result as a button
                st.button(label, key=f"sr_{i}", on_click=_go, args=(key, state), use_container_width=True)


# --- Page furniture ------------------------------------------------------------
# Functions that render page titles, cards, charts headers, etc.

def page_header(title, subtitle, right_html=""):
    """Render a page header with title, subtitle, and optional right-side HTML.
    
    Parameters
    ----------
    title : str
        Main page title.
    subtitle : str
        Subtitle text below the title.
    right_html : str
        Optional HTML to show on the right side (e.g. a chip).
    """
    md(f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap">'
       f'<div><div class="pp-h1">{esc(title)}</div><div class="pp-sub">{esc(subtitle)}</div></div>'
       f'<div style="padding-top:.5rem">{right_html}</div></div>')


def chip(text, icon=None, boxed=False, sub=None):
    """Create a small status chip (badge-like element).
    
    Parameters
    ----------
    text : str
        Chip text.
    icon : str or None
        Icon key from ICONS dict, or None for a simple dot.
    boxed : bool
        If True, add a boxed style class.
    sub : str or None
        Optional subtitle text below the main text.
    
    Returns
    -------
    str
        HTML string for the chip.
    """
    glyph = ICONS[icon] if icon else '<i class="pp-dot"></i>'  # Get SVG icon or a simple dot
    body = f'<span>{esc(text)}</span>' if not sub else f'<span><b>{esc(text)}</b><br>{esc(sub)}</span>'
    return f'<span class="pp-chip{" pp-chip-box" if boxed else ""}">{glyph}{body}</span>'


def filter_title(title, subtitle, icon="trend"):
    """Render a filter bar title with icon.
    
    Parameters
    ----------
    title : str
        Filter section title.
    subtitle : str
        Subtitle text.
    icon : str
        Icon key from ICONS dict.
    """
    md(f'<div class="pp-fhead"><span class="pp-fic">{ICONS[icon]}</span><div><b>{esc(title)}</b><span>{esc(subtitle)}</span></div></div>')


def filter_stat(label, value, sub="", tone=""):
    """Render a selected-value summary at the right of a filter bar.
    
    Parameters
    ----------
    label : str
        Label for the stat.
    value : str
        Value to display.
    sub : str
        Subtext below the label.
    tone : str
        CSS tone class for styling.
    """
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
    """Create a pill-shaped badge.
    
    Parameters
    ----------
    text : str
        Pill text.
    tone : str
        CSS tone class.
    dot : bool
        If True, add a small dot before the text.
    
    Returns
    -------
    str
        HTML string for the pill.
    """
    return f'<span class="pp-pill {tone}">{"<i class=pp-dot></i>" if dot else ""}{esc(text)}</span>'


def panel_header(title, subtitle=None, right=None, icon="chart"):
    """Render a section header with icon, title, subtitle, and optional right content.
    
    Parameters
    ----------
    title : str
        Section title.
    subtitle : str or None
        Optional subtitle.
    right : str or None
        Optional HTML for the right side.
    icon : str
        Icon key from ICONS dict (default "chart").
    """
    icon = ICONS.get(icon, icon)  # Get SVG icon, or use the string as-is if not in ICONS
    md(f'<div class="pp-ph">{icon}<div><h3>{esc(title)}</h3>{f"<p>{esc(subtitle)}</p>" if subtitle else ""}</div>'
       f'{f"<div class=pp-right>{esc(right)}</div>" if right else ""}</div>')


def kpi_card(label, value, badge, delta=None, bad=None, tone="green", foot="vs. last month", help=None):
    """Render a KPI (key performance indicator) summary card.
    
    Parameters
    ----------
    label : str
        Card label (e.g. "CPI", "Inflation Rate").
    value : str
        Main value (formatted by theme.format_value()).
    badge : str
        Small badge text (e.g. "CPI", "%", "₱").
    delta : str or None
        Change text (e.g. "+0.8 pts").
    bad : bool or None
        True = red (bad change), False = green (good change), None = grey.
    tone : str
        CSS tone class for the card background.
    foot : str
        Footer text (e.g. "vs. last month").
    help : str or None
        Tooltip text shown on an info icon.
    """
    cls = {True: "bad", False: "good", None: "flat"}[bad]  # CSS class for delta colour
    delta_html = f'<span class="pp-d {cls}">{esc(delta)}</span>' if delta else ""  # Delta HTML if provided
    info = f'<span class="pp-info" title="{esc(help)}">i</span>' if help else ""  # Info icon if help text provided
    md(f'<div class="pp-kpi {tone}"><div class="pp-badge">{esc(badge)}</div><div class="pp-lab">{esc(label)}{info}</div>'
       f'<div class="pp-val">{esc(value)}{delta_html}</div><div class="pp-foot">{esc(foot)}</div></div>')


def mini_card(label, value, top_right="", bottom_right="", tone="green"):
    """Render a small mini card (used for stats in side panels).
    
    Parameters
    ----------
    label : str
        Card label.
    value : str
        Main value.
    top_right : str
        Top right value.
    bottom_right : str
        Bottom right value.
    tone : str
        CSS tone class.
    """
    md(f'<div class="pp-mini {tone}"><div class="pp-ml">{esc(label)}</div><div class="pp-row"><div class="pp-mv">{esc(value)}</div>'
       f'<div style="text-align:right"><div class="pp-ms" style="font-weight:700">{esc(top_right)}</div>'
       f'<div class="pp-ms">{esc(bottom_right)}</div></div></div></div>')


def insight_card(title, items, icon="bulb"):
    """Render an insight card with a title and bulleted items.
    
    Parameters
    ----------
    title : str
        Card title.
    items : list of tuples
        Each tuple is (heading, body) for one bullet point.
    icon : str
        Icon key from ICONS dict.
    """
    icon = ICONS.get(icon, esc(icon))  # Get SVG icon
    rows = "".join(f"<li>{f'<b>{esc(h)}</b>' if h else ''}{esc(b)}</li>" for h, b in items)  # Build bullet list
    md(f'<div class="pp-insight"><h4><span class="pp-ih">{icon}</span>{esc(title)}</h4><ul>{rows}</ul></div>')


def ranked_list(rows):
    """Render a ranked list with ranks, names, and change percentages.
    
    Parameters
    ----------
    rows : list of dicts
        Each dict has keys: rank, name, sub, change (float percent).
    """
    items = []
    for r in rows:
        neg = " neg" if r["change"] < 0 else ""  # CSS class for negative change colour
        items.append(f'<div class="pp-li"><span class="pp-rk">{r["rank"]}</span>'
                     f'<span class="pp-circ">{esc(r["name"][:1])}</span>'  # First letter of name in a circle
                     f'<span class="pp-nm">{esc(r["name"])}<small>{esc(r.get("sub", ""))}</small></span>'  # Name + subtext
                     f'<span class="pp-ch{neg}">{r["change"]:+.1f}%</span></div>')  # Change with sign
    md(f'<div class="pp-list">{"".join(items)}</div>')


def rank_color(i, n, higher_is_better):
    """Get a colour for a ranked row based on its position.
    
    For cost indicators (CPI, inflation), higher value = worse, so the highest
    gets a warm colour. For purchasing power, higher = better.
    
    Parameters
    ----------
    i : int
        Row index (0 = highest value).
    n : int
        Total number of rows.
    higher_is_better : bool
        Whether higher values are better.
    
    Returns
    -------
    str
        Hex colour string.
    """
    palette = tokens.RANK_COLORS if higher_is_better else tokens.RANK_COLORS[::-1]  # Pick palette direction
    return palette[min(len(palette) - 1, int(i * len(palette) / max(n, 1)))]  # Interpolate colour from palette


def rank_legend(higher_is_better):
    """Render a colour legend for ranked lists.
    
    Parameters
    ----------
    higher_is_better : bool
        Whether higher values are better (affects colour order).
    """
    top, mid, low = (tokens.RANK_COLORS[0], tokens.RANK_COLORS[2], tokens.RANK_COLORS[4])
    if not higher_is_better:
        top, low = low, top  # Swap top and low for cost indicators
    names = ("Higher value", "Mid-range", "Lower value")
    md('<div class="pp-legend">' + "".join(f'<span><i style="background:{c}"></i>{n}</span>'
                                          for c, n in zip((top, mid, low), names)) + '</div>')


def quote_card(text="Informed households build a more resilient Philippine economy."):
    """Render a quote card.
    
    Parameters
    ----------
    text : str
        Quote text.
    """
    md(f'<div class="pp-quote">{esc(text)}<i></i></div>')


def footer():
    """Render the page footer with PSA attribution and forecast disclaimer."""
    md(f'<div class="pp-foot-note">{esc(tokens.PSA_ATTRIBUTION)}<br><b>Forecast disclaimer:</b> '
       f'{esc(tokens.FORECAST_DISCLAIMER)}</div>')
