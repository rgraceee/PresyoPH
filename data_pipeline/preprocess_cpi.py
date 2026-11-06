"""Preprocess raw CPI Excel files into one cleaned CSV.

Reads CPI_1.xlsx, CPI_2.xlsx and CPI_3.xlsx from datasets/raw/,
converts each from wide format (months as columns) to long format
(date, area, category, value, base_year), then merges them into
datasets/processed/cpi_clean.csv.

CPI_3 already covers 2023, so only CPI_2's 2022 rows are kept to avoid
duplicating 2023 observations.
"""

from pathlib import Path

import pandas as pd


# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "datasets" / "raw"
PROCESSED_DIR = BASE_DIR / "datasets" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# REUSABLE CPI FILE PARSER
# --------------------------------------------------

def read_cpi_file(path, expected_months):
    """Parse one raw CPI Excel file into a long DataFrame.

    Parameters
    ----------
    path : Path
        Excel file to read (no header row).
    expected_months : int
        How many monthly columns each area/category should have,
        used only for the validation message.

    Returns
    -------
    pandas.DataFrame
        Columns: date, area, category, value, base_year.
    """
    raw = pd.read_excel(path, header=None)

    # Observation rows start after the 4 header rows.
    data = raw.iloc[4:1684].copy()

    # PSA repeats area names only on the first row of each block;
    # forward-fill so every row knows its area.
    data[0] = data[0].ffill()

    # Row 2 = year, row 3 = period (e.g. "Jan"). Skip "Ave" columns.
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

    # Convert wide layout to one row per (date, area, category).
    records = []
    for item in monthly_columns:
        col = item["column"]
        date = pd.to_datetime(f"{item['year']}-{item['month']}", format="%Y-%b")
        for _, row in data.iterrows():
            records.append({
                "date": date,
                "area": row[0],
                "category": row[1],
                "value": row[col],
                "base_year": 2018,
            })

    long_df = pd.DataFrame(records)
    long_df["value"] = pd.to_numeric(long_df["value"], errors="coerce")

    # Validation summary.
    obs_rows = len(data)
    actual_rows = len(long_df)
    duplicates = long_df.duplicated(subset=["date", "area", "category"]).sum()
    coverage = long_df.groupby(["area", "category"])["date"].nunique()

    print(f"\n--- {path.name} VALIDATION ---")
    print("Observation rows:", obs_rows)
    print("Monthly columns:", len(monthly_columns))
    print("Expected rows:", obs_rows * len(monthly_columns))
    print("Actual rows:", actual_rows)
    print("Duplicate observations:", duplicates)
    print("Unique areas:", long_df["area"].nunique())
    print("Unique categories:", long_df["category"].nunique())
    print("Date range:", long_df["date"].min(), "to", long_df["date"].max())
    print("Minimum months per area/category:", coverage.min())
    print("Maximum months per area/category:", coverage.max())

    return long_df


# --------------------------------------------------
# LOAD AND VALIDATE EACH CPI FILE
# --------------------------------------------------

cpi1_long = read_cpi_file(RAW_DIR / "CPI_1.xlsx", expected_months=48)
cpi2_long = read_cpi_file(RAW_DIR / "CPI_2.xlsx", expected_months=24)

cpi3_raw = pd.read_excel(RAW_DIR / "CPI_3.xlsx", header=None)
cpi3_data = cpi3_raw.iloc[4:1684].copy()
cpi3_data[0] = cpi3_data[0].ffill()
years3 = cpi3_raw.iloc[2].ffill()
periods3 = cpi3_raw.iloc[3]
monthly_columns3 = []
for col in range(2, cpi3_raw.shape[1]):
    year = years3.iloc[col]
    period = periods3.iloc[col]
    if pd.notna(year) and period != "Ave":
        monthly_columns3.append({"column": col, "year": int(year), "month": period})

records3 = []
for item in monthly_columns3:
    col = item["column"]
    date = pd.to_datetime(f"{item['year']}-{item['month']}", format="%Y-%b")
    for _, row in cpi3_data.iterrows():
        value = pd.to_numeric(row[col], errors="coerce")
        records3.append({
            "date": date,
            "area": row[0],
            "category": row[1],
            "value": value,
            "base_year": 2018,
        })

cpi3_long = pd.DataFrame(records3)
# Remove unavailable PSA values such as "..".
cpi3_long = cpi3_long.dropna(subset=["value"]).copy()

duplicates3 = cpi3_long.duplicated(subset=["date", "area", "category"]).sum()
coverage3 = cpi3_long.groupby(["area", "category"])["date"].nunique()
expected_months3 = 44
expected_rows3 = len(cpi3_data) * expected_months3

print("\n--- CPI_3 VALIDATION ---")
print("Observation rows:", len(cpi3_data))
print("Monthly columns found:", len(monthly_columns3))
print("Actual records after removing unavailable values:", len(cpi3_long))
print("Duplicate observations:", duplicates3)
print("Unique areas:", cpi3_long["area"].nunique())
print("Unique categories:", cpi3_long["category"].nunique())
print("Date range:", cpi3_long["date"].min(), "to", cpi3_long["date"].max())
print("Minimum months per area/category:", coverage3.min())
print("Maximum months per area/category:", coverage3.max())
print("Expected valid rows:", expected_rows3)
print("Actual valid rows:", len(cpi3_long))


# --------------------------------------------------
# MERGE COMPLETE CPI DATASET
# --------------------------------------------------

# CPI_3 already contains 2023, so keep only 2022 from CPI_2 to avoid
# duplicating 2023 observations.
cpi2_2022 = cpi2_long[cpi2_long["date"].dt.year == 2022].copy()

cpi_clean = pd.concat([cpi1_long, cpi2_2022, cpi3_long], ignore_index=True)
cpi_clean = cpi_clean.sort_values(by=["date", "area", "category"]).reset_index(drop=True)


# --------------------------------------------------
# VALIDATE COMPLETE CPI
# --------------------------------------------------

final_duplicates = cpi_clean.duplicated(subset=["date", "area", "category"]).sum()
total_months = cpi_clean["date"].nunique()
final_coverage = cpi_clean.groupby(["area", "category"])["date"].nunique()

expected_months = 104
expected_final_rows = (
    cpi_clean["area"].nunique()
    * cpi_clean["category"].nunique()
    * expected_months
)

final_validation_passed = (
    len(cpi_clean) == expected_final_rows
    and total_months == expected_months
    and cpi_clean["value"].isna().sum() == 0
    and final_duplicates == 0
    and final_coverage.min() == expected_months
    and final_coverage.max() == expected_months
)

print("\n--- COMPLETE CPI VALIDATION ---")
print("Total records:", len(cpi_clean))
print("Date range:", cpi_clean["date"].min(), "to", cpi_clean["date"].max())
print("Unique areas:", cpi_clean["area"].nunique())
print("Unique categories:", cpi_clean["category"].nunique())
print("Missing values:")
print(cpi_clean.isna().sum())
print("Duplicate observations:", final_duplicates)
print("Total unique months:", total_months)
print("Minimum months per area/category:", final_coverage.min())
print("Maximum months per area/category:", final_coverage.max())
print("Expected total rows:", expected_final_rows)
print("Actual total rows:", len(cpi_clean))
print("COMPLETE CPI VALIDATION PASSED:", final_validation_passed)


# --------------------------------------------------
# SAVE CLEANED CPI
# --------------------------------------------------

if final_validation_passed:
    cpi_output = PROCESSED_DIR / "cpi_clean.csv"
    cpi_clean.to_csv(cpi_output, index=False, date_format="%Y-%m-%d")
    print("\nCPI preprocessing completed successfully.")
    print("Saved to:", cpi_output)
    print("Rows exported:", len(cpi_clean))
else:
    print("\nCPI was NOT exported because validation failed.")
