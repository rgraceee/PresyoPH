"""
================================================================================
FILE: app/ui/queries.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
This file contains small data helper functions that the newer Streamlit pages
need but that backend/data.py doesn't have yet. They are built only from
backend/data's public functions, so the backend is untouched.

If the backend later gains equivalent functions, the callers can be switched
over and the duplicates here can be deleted.

Functions:
  - list_region_groups(): island groups (Luzon, Visayas, Mindanao) + "All Regions"
  - regions_in_group(): list of regions in a given island group
  - region_group_of(): which island group a region belongs to
  - get_category_changes(): percent change in each commodity group's CPI over N months
  - get_table(): long-format table for the Data Explorer

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- app/pages/dashboard.py: Calls queries.get_category_changes() for top increases card.
- app/pages/categories.py: Calls queries.get_category_changes() for fastest-rising categories.
- app/pages/regional.py: Calls queries.list_region_groups(), queries.regions_in_group(), queries.region_group_of().
- app/pages/reports.py: Calls queries.get_category_changes() for cost of living summary.
- app/pages/data_explorer.py: Calls queries.get_table() for the data explorer table.
- app/ui/shell.py: Calls queries.region_group_of() for search results.
- backend/data.py: Calls data.get_category_comparison(), data.get_series(), data.list_categories(), data.get_date_range().

================================================================================
"""

"""Small data helpers the new screens need that backend/data.py does not have.

They are built only from backend.data's public functions, so the backend is
untouched. If the backend later gains equivalents, switch the callers over and
delete the duplicates here.
"""

import pandas as pd                                  # pandas: DataFrame manipulation

from backend import data                             # backend data access layer

# Island groups of PSA's regions, for the Regional Comparison filter.
# The 18 regions are grouped into Luzon, Visayas, and Mindanao.
REGION_GROUPS = {
    "Luzon": ["National Capital Region (NCR)", "Cordillera Administrative Region (CAR)", "Region I (Ilocos Region)",
              "Region II (Cagayan Valley)", "Region III (Central Luzon)", "Region IV-A (CALABARZON)",
              "MIMAROPA Region", "Region V (Bicol Region)"],
    "Visayas": ["Region VI (Western Visayas)", "Negros Island Region (NIR)", "Region VII (Central Visayas)",
                "Region VIII (Eastern Visayas)"],
    "Mindanao": ["Region IX (Zamboanga Peninsula)", "Region X (Northern Mindanao)", "Region XI (Davao Region)",
                 "Region XII (SOCCSKSARGEN)", "Region XIII (Caraga)",
                 "Bangsamoro Autonomous Region in Muslim Mindanao (BARMM)"],
}


def list_region_groups():
    """Return region group options for dropdowns: ["All Regions", "Luzon", "Visayas", "Mindanao"].
    
    Returns
    -------
    list of str
        Region group names.
    """
    return ["All Regions"] + list(REGION_GROUPS)       # "All Regions" plus the three island group keys


def regions_in_group(group):
    """Return the list of regions in a given island group.
    
    Parameters
    ----------
    group : str
        One of "All Regions", "Luzon", "Visayas", "Mindanao".
    
    Returns
    -------
    list of str
        Region names in that group.
    
    Raises
    ------
    ValueError
        If group is not a valid group name.
    """
    if group == "All Regions":                           # Special case: return all 18 regions
        return list(data.list_areas("region"))
    if group not in REGION_GROUPS:                       # Validate group name
        raise ValueError(f"Unknown region group {group!r}.")
    return list(REGION_GROUPS[group])                    # Return regions for this group


def region_group_of(region):
    """Return which island group a region belongs to.
    
    Parameters
    ----------
    region : str
        Region name.
    
    Returns
    -------
    str
        Island group name ("Luzon", "Visayas", "Mindanao"), or "" if not found.
    """
    for group, names in REGION_GROUPS.items():           # Check each group
        if region in names:                              # If region is in this group
            return group                                 # Return the group name
    return ""                                            # Not found in any group


def get_category_changes(months=1, date=None, area=data.NATIONAL):
    """Calculate percent change in each commodity group's CPI over N months.
    
    Default: latest month vs. the month before (1 month change).
    Results are ranked from biggest rise to biggest fall.
    
    Parameters
    ----------
    months : int
        Number of months to look back (default 1).
    date : str or pd.Timestamp or None
        End date for the comparison. None means the latest available month.
    area : str
        Area name (default "PHILIPPINES").
    
    Returns
    -------
    pandas.DataFrame
        Columns: rank, item, code, label, change_pct, value.
        The frame's attrs dict contains: start, end, months, area, all_items.
    """
    end = pd.Timestamp(date) if date is not None else data.get_date_range("cpi")[1]  # End date (latest if None)
    start = end - pd.DateOffset(months=months)           # Start date = end minus N months
    now = data.get_category_comparison("cpi", end, area) # CPI values at end date for all groups
    before = data.get_category_comparison("cpi", start, area).set_index("item")["value"]  # CPI values at start date
    now_idx = now.set_index("item")                      # Index by item for alignment
    # Percent change: (now / before - 1) * 100, sorted descending, drop missing
    change = ((now_idx["value"] / before.reindex(now_idx.index) - 1) * 100).dropna().sort_values(ascending=False)
    out = pd.DataFrame({                               # Build output DataFrame
        "rank": range(1, len(change) + 1),             # Rank numbers
        "item": change.index,                          # Full PSA item labels
        "code": now_idx.loc[change.index, "code"].values,  # 2-digit codes
        "label": now_idx.loc[change.index, "label"].values,  # Short display names
        "change_pct": change.values,                   # Percent change values
        "value": now_idx.loc[change.index, "value"].values,  # Current CPI values
    })
    # Calculate all-items percent change for metadata
    all_now = now.attrs.get("all_items")               # All-items CPI at end date
    all_before = data.get_series("cpi", start, start, area=area).iloc[0]["value"]  # All-items CPI at start date
    out.attrs.update({"start": start, "end": end, "months": months, "area": area,
                      "all_items": (all_now / all_before - 1) * 100 if all_now is not None else None})
    return out


def get_table(indicator, start=None, end=None, areas=None, items=None):
    """Build a long-format table for the Data Explorer.
    
    Parameters
    ----------
    indicator : str
        One of "cpi", "inflation", "purchasing_power".
    start, end : str or pd.Timestamp or None
        Date range filter.
    areas : list of str or None
        Areas to include. None means national only.
    items : list of str or None
        Items to include. None means all items.
    
    Returns
    -------
    pandas.DataFrame
        Columns: date, area, category, value (or date, area, value for purchasing power).
    """
    areas = areas or [data.NATIONAL]                     # Default to national if no areas specified
    if indicator == "purchasing_power":                  # Purchasing power has no category breakdown
        items = [data.ALL_ITEMS]
    elif items is None:                                  # Default to all items
        items = [data.ALL_ITEMS]
    # Build a lookup: item label -> short display name
    labels = dict(zip(*(data.list_categories(True)[c] for c in ("item", "label"))))
    parts = []
    for area in areas:                                   # One series per (area, item) combination
        for item in items:
            part = data.get_series(indicator, start, end, area=area, item=item).assign(
                area=area, category=labels.get(item, item))  # Add area and category columns
            parts.append(part)
    out = pd.concat(parts, ignore_index=True).sort_values(["date", "area", "category"])  # Combine all series
    # Purchasing power has no category column
    cols = ["date", "area", "value"] if indicator == "purchasing_power" else ["date", "area", "category", "value"]
    return out[cols].reset_index(drop=True)              # Return selected columns with clean index
