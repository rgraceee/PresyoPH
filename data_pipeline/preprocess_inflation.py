"""Preprocess raw Inflation Excel files into one cleaned CSV."""

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "datasets" / "raw"
PROCESSED_DIR = BASE_DIR / "datasets" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def read_inflation_file(path, expected_months):
    raw = pd.read_excel(path, header=None)

    data = raw.iloc[4:1684].copy()
    data[0] = data[0].ffill()

    years = raw.iloc[2].ffill()
    periods = raw.iloc[3]

    monthly_columns = []
    for col in range(2, raw.shape[1]):
        year = years.iloc[col]
        period = periods.iloc[col]
        if pd.notna(year) and period != "Ave":
            monthly_columns.append({
                "column": col,
                "year": int(year),
                "month": period,
            })

    records = []
    for item in monthly_columns:
        col = item["column"]
        date = pd.to_datetime(f"{item['year']}-{item['month']}", format="%Y-%b")
        for _, row in data.iterrows():
            value = pd.to_numeric(row[col], errors="coerce")
            records.append({
                "date": date,
                "area": row[0],
                "category": row[1],
                "value": value,
                "unit": "percent",
            })

    long_df = pd.DataFrame(records)

    obs_rows = len(data)
    actual_rows = len(long_df)
    duplicates = long_df.duplicated(subset=["date", "area", "category"]).sum()
    coverage = long_df.groupby(["area", "category"])["date"].nunique()

    print(f"\n--- {path.name} VALIDATION ---")
    print("Observation rows:", obs_rows)
    print("Monthly columns found:", len(monthly_columns))
    print("Expected rows:", obs_rows * len(monthly_columns))
    print("Actual records after removing unavailable values:", actual_rows)
    print("Duplicate observations:", duplicates)
    print("Unique areas:", long_df["area"].nunique())
    print("Unique categories:", long_df["category"].nunique())
    print("Date range:", long_df["date"].min(), "to", long_df["date"].max())
    print("Minimum months per area/category:", coverage.min())
    print("Maximum months per area/category:", coverage.max())
    print("Expected valid rows:", obs_rows * expected_months)
    print("Actual valid rows:", len(long_df))

    return long_df


inflation1_long = read_inflation_file(RAW_DIR / "Inflation_1.xlsx", expected_months=48)

inflation2_long = read_inflation_file(RAW_DIR / "Inflation_2.xlsx", expected_months=44)
inflation2_long = inflation2_long.dropna(subset=["value"]).copy()


inflation_clean = pd.concat([inflation1_long, inflation2_long], ignore_index=True)
inflation_clean = inflation_clean.sort_values(
    by=["date", "area", "category"]
).reset_index(drop=True)


final_duplicates = inflation_clean.duplicated(
    subset=["date", "area", "category"]
).sum()
total_months = inflation_clean["date"].nunique()
final_coverage = (
    inflation_clean
    .groupby(["area", "category"])["date"]
    .nunique()
)

expected_months = 92
expected_final_rows = (
    inflation_clean["area"].nunique()
    * inflation_clean["category"].nunique()
    * expected_months
)

final_validation_passed = (
    len(inflation_clean) == expected_final_rows
    and total_months == expected_months
    and inflation_clean["value"].isna().sum() == 0
    and final_duplicates == 0
    and final_coverage.min() == expected_months
    and final_coverage.max() == expected_months
)

print("\n--- COMPLETE INFLATION VALIDATION ---")
print("Total records:", len(inflation_clean))
print(
    "Date range:",
    inflation_clean["date"].min(),
    "to",
    inflation_clean["date"].max()
)
print("Unique areas:", inflation_clean["area"].nunique())
print("Unique categories:", inflation_clean["category"].nunique())
print("Missing values:")
print(inflation_clean.isna().sum())
print("Duplicate observations:", final_duplicates)
print("Total unique months:", total_months)
print(
    "Minimum months per area/category:",
    final_coverage.min()
)
print(
    "Maximum months per area/category:",
    final_coverage.max()
)
print("Expected total rows:", expected_final_rows)
print("Actual total rows:", len(inflation_clean))
print(
    "COMPLETE INFLATION VALIDATION PASSED:",
    final_validation_passed
)


if final_validation_passed:
    inflation_output = PROCESSED_DIR / "inflation_clean.csv"
    inflation_clean.to_csv(
        inflation_output,
        index=False,
        date_format="%Y-%m-%d"
    )

    print("\nInflation preprocessing completed successfully.")
    print("Saved to:", inflation_output)
    print("Rows exported:", len(inflation_clean))
else:
    print(
        "\nInflation was NOT exported because validation failed."
    )
