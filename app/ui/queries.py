"""Small data helpers the new screens need that backend/data.py does not have."""

import pandas as pd

from backend import data

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
    return ["All Regions"] + list(REGION_GROUPS)


def regions_in_group(group):
    if group == "All Regions":
        return list(data.list_areas("region"))
    if group not in REGION_GROUPS:
        raise ValueError(f"Unknown region group {group!r}.")
    return list(REGION_GROUPS[group])


def region_group_of(region):
    for group, names in REGION_GROUPS.items():
        if region in names:
            return group
    return ""


def get_category_changes(months=1, date=None, area=data.NATIONAL):
    end = pd.Timestamp(date) if date is not None else data.get_date_range("cpi")[1]
    start = end - pd.DateOffset(months=months)
    now = data.get_category_comparison("cpi", end, area)
    before = data.get_category_comparison("cpi", start, area).set_index("item")["value"]
    now_idx = now.set_index("item")
    change = ((now_idx["value"] / before.reindex(now_idx.index) - 1) * 100).dropna().sort_values(ascending=False)
    out = pd.DataFrame({
        "rank": range(1, len(change) + 1),
        "item": change.index,
        "code": now_idx.loc[change.index, "code"].values,
        "label": now_idx.loc[change.index, "label"].values,
        "change_pct": change.values,
        "value": now_idx.loc[change.index, "value"].values,
    })
    all_now = now.attrs.get("all_items")
    all_before = data.get_series("cpi", start, start, area=area).iloc[0]["value"]
    out.attrs.update({"start": start, "end": end, "months": months, "area": area,
                      "all_items": (all_now / all_before - 1) * 100 if all_now is not None else None})
    return out


def get_table(indicator, start=None, end=None, areas=None, items=None):
    areas = areas or [data.NATIONAL]
    if indicator == "purchasing_power":
        items = [data.ALL_ITEMS]
    elif items is None:
        items = [data.ALL_ITEMS]
    labels = dict(zip(*(data.list_categories(True)[c] for c in ("item", "label"))))
    parts = []
    for area in areas:
        for item in items:
            part = data.get_series(indicator, start, end, area=area, item=item).assign(
                area=area, category=labels.get(item, item))
            parts.append(part)
    out = pd.concat(parts, ignore_index=True).sort_values(["date", "area", "category"])
    cols = ["date", "area", "value"] if indicator == "purchasing_power" else ["date", "area", "category", "value"]
    return out[cols].reset_index(drop=True)
