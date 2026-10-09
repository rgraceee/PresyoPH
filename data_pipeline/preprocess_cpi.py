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
# CPI FILES
# --------------------------------------------------

CPI_1_FILE = RAW_DIR / "CPI_1.xlsx"
CPI_2_FILE = RAW_DIR / "CPI_2.xlsx"
CPI_3_FILE = RAW_DIR / "CPI_3.xlsx"


# ==================================================
# CPI_1
# ==================================================

cpi1_raw = pd.read_excel(CPI_1_FILE, header=None)

# Actual observation rows
cpi1_data = cpi1_raw.iloc[4:1684].copy()

# Fill geographic area labels
cpi1_data[0] = cpi1_data[0].ffill()

# Identify monthly columns
years1 = cpi1_raw.iloc[2].ffill()
periods1 = cpi1_raw.iloc[3]

monthly_columns1 = []

for col in range(2, cpi1_raw.shape[1]):
    year = years1.iloc[col]
    period = periods1.iloc[col]

    if pd.notna(year) and period != "Ave":
        monthly_columns1.append({
            "column": col,
            "year": int(year),
            "month": period
        })


# Convert wide to long format
records1 = []

for item in monthly_columns1:
    col = item["column"]
    year = item["year"]
    month = item["month"]

    date = pd.to_datetime(
        f"{year}-{month}",
        format="%Y-%b"
    )

    for _, row in cpi1_data.iterrows():
        records1.append({
            "date": date,
            "area": row[0],
            "category": row[1],
            "value": row[col],
            "base_year": 2018
        })


cpi1_long = pd.DataFrame(records1)

cpi1_long["value"] = pd.to_numeric(
    cpi1_long["value"],
    errors="coerce"
)


# --------------------------------------------------
# VALIDATE CPI_1
# --------------------------------------------------

expected_rows1 = len(cpi1_data) * len(monthly_columns1)
actual_rows1 = len(cpi1_long)

duplicates1 = cpi1_long.duplicated(
    subset=["date", "area", "category"]
).sum()

coverage1 = (
    cpi1_long
    .groupby(["area", "category"])["date"]
    .nunique()
)

validation_passed1 = (
    expected_rows1 == actual_rows1
    and cpi1_long["value"].isna().sum() == 0
    and duplicates1 == 0
    and coverage1.min() == 48
    and coverage1.max() == 48
)

print("\n--- CPI_1 VALIDATION ---")
print("Observation rows:", len(cpi1_data))
print("Monthly columns:", len(monthly_columns1))
print("Expected rows:", expected_rows1)
print("Actual rows:", actual_rows1)
print("Duplicate observations:", duplicates1)
print("Unique areas:", cpi1_long["area"].nunique())
print("Unique categories:", cpi1_long["category"].nunique())
print("Date range:", cpi1_long["date"].min(), "to", cpi1_long["date"].max())
print("Minimum months per area/category:", coverage1.min())
print("Maximum months per area/category:", coverage1.max())
print("CPI_1 VALIDATION PASSED:", validation_passed1)


# ==================================================
# CPI_2
# ==================================================

cpi2_raw = pd.read_excel(CPI_2_FILE, header=None)

cpi2_data = cpi2_raw.iloc[4:1684].copy()

# Fill geographic area labels
cpi2_data[0] = cpi2_data[0].ffill()

# Identify monthly columns
years2 = cpi2_raw.iloc[2].ffill()
periods2 = cpi2_raw.iloc[3]

monthly_columns2 = []

for col in range(2, cpi2_raw.shape[1]):
    year = years2.iloc[col]
    period = periods2.iloc[col]

    if pd.notna(year) and period != "Ave":
        monthly_columns2.append({
            "column": col,
            "year": int(year),
            "month": period
        })


# Convert wide to long format
records2 = []

for item in monthly_columns2:
    col = item["column"]
    year = item["year"]
    month = item["month"]

    date = pd.to_datetime(
        f"{year}-{month}",
        format="%Y-%b"
    )

    for _, row in cpi2_data.iterrows():
        records2.append({
            "date": date,
            "area": row[0],
            "category": row[1],
            "value": row[col],
            "base_year": 2018
        })


cpi2_long = pd.DataFrame(records2)

cpi2_long["value"] = pd.to_numeric(
    cpi2_long["value"],
    errors="coerce"
)


# --------------------------------------------------
# VALIDATE CPI_2
# --------------------------------------------------

expected_rows2 = len(cpi2_data) * len(monthly_columns2)
actual_rows2 = len(cpi2_long)

duplicates2 = cpi2_long.duplicated(
    subset=["date", "area", "category"]
).sum()

coverage2 = (
    cpi2_long
    .groupby(["area", "category"])["date"]
    .nunique()
)

validation_passed2 = (
    expected_rows2 == actual_rows2
    and cpi2_long["value"].isna().sum() == 0
    and duplicates2 == 0
    and coverage2.min() == 24
    and coverage2.max() == 24
)

print("\n--- CPI_2 VALIDATION ---")
print("Observation rows:", len(cpi2_data))
print("Monthly columns:", len(monthly_columns2))
print("Expected rows:", expected_rows2)
print("Actual rows:", actual_rows2)
print("Duplicate observations:", duplicates2)
print("Unique areas:", cpi2_long["area"].nunique())
print("Unique categories:", cpi2_long["category"].nunique())
print("Date range:", cpi2_long["date"].min(), "to", cpi2_long["date"].max())
print("Minimum months per area/category:", coverage2.min())
print("Maximum months per area/category:", coverage2.max())
print("CPI_2 VALIDATION PASSED:", validation_passed2)


# ==================================================
# CPI_3
# ==================================================

cpi3_raw = pd.read_excel(CPI_3_FILE, header=None)

cpi3_data = cpi3_raw.iloc[4:1684].copy()

# Fill geographic area labels
cpi3_data[0] = cpi3_data[0].ffill()

# Identify monthly columns
years3 = cpi3_raw.iloc[2].ffill()
periods3 = cpi3_raw.iloc[3]

monthly_columns3 = []

for col in range(2, cpi3_raw.shape[1]):
    year = years3.iloc[col]
    period = periods3.iloc[col]

    if pd.notna(year) and period != "Ave":
        monthly_columns3.append({
            "column": col,
            "year": int(year),
            "month": period
        })


# Convert wide to long format
records3 = []

for item in monthly_columns3:
    col = item["column"]
    year = item["year"]
    month = item["month"]

    date = pd.to_datetime(
        f"{year}-{month}",
        format="%Y-%b"
    )

    for _, row in cpi3_data.iterrows():

        value = pd.to_numeric(
            row[col],
            errors="coerce"
        )

        records3.append({
            "date": date,
            "area": row[0],
            "category": row[1],
            "value": value,
            "base_year": 2018
        })


cpi3_long = pd.DataFrame(records3)

# Remove unavailable PSA values such as ".."
cpi3_long = cpi3_long.dropna(
    subset=["value"]
).copy()


# --------------------------------------------------
# VALIDATE CPI_3
# --------------------------------------------------

duplicates3 = cpi3_long.duplicated(
    subset=["date", "area", "category"]
).sum()

coverage3 = (
    cpi3_long
    .groupby(["area", "category"])["date"]
    .nunique()
)

expected_months3 = 44
expected_rows3 = len(cpi3_data) * expected_months3

validation_passed3 = (
    expected_rows3 == len(cpi3_long)
    and cpi3_long["value"].isna().sum() == 0
    and duplicates3 == 0
    and coverage3.min() == expected_months3
    and coverage3.max() == expected_months3
)

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
print("CPI_3 VALIDATION PASSED:", validation_passed3)


# ==================================================
# CHECK CPI_2 / CPI_3 2023 OVERLAP
# ==================================================

cpi2_2023 = cpi2_long[
    cpi2_long["date"].dt.year == 2023
].copy()

cpi3_2023 = cpi3_long[
    cpi3_long["date"].dt.year == 2023
].copy()

comparison = cpi2_2023.merge(
    cpi3_2023,
    on=["date", "area", "category"],
    how="outer",
    suffixes=("_cpi2", "_cpi3"),
    indicator=True
)

comparison["values_match"] = (
    comparison["value_cpi2"] == comparison["value_cpi3"]
)

matching = comparison["values_match"].sum()
different = (~comparison["values_match"]).sum()

print("\n--- CPI 2023 OVERLAP CHECK ---")
print("CPI_2 2023 records:", len(cpi2_2023))
print("CPI_3 2023 records:", len(cpi3_2023))
print("Matching values:", matching)
print("Different values:", different)


# ==================================================
# MERGE COMPLETE CPI DATASET
# ==================================================

# CPI_3 already contains 2023, so keep only 2022
# from CPI_2 to avoid duplicate observations.

cpi2_2022 = cpi2_long[
    cpi2_long["date"].dt.year == 2022
].copy()

cpi_clean = pd.concat(
    [
        cpi1_long,
        cpi2_2022,
        cpi3_long
    ],
    ignore_index=True
)

cpi_clean = cpi_clean.sort_values(
    by=["date", "area", "category"]
).reset_index(drop=True)


# --------------------------------------------------
# VALIDATE COMPLETE CPI
# --------------------------------------------------

final_duplicates = cpi_clean.duplicated(
    subset=["date", "area", "category"]
).sum()

total_months = cpi_clean["date"].nunique()

final_coverage = (
    cpi_clean
    .groupby(["area", "category"])["date"]
    .nunique()
)

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

    cpi_clean.to_csv(
        cpi_output,
        index=False,
        date_format="%Y-%m-%d"
    )

    print("\nCPI preprocessing completed successfully.")
    print("Saved to:", cpi_output)
    print("Rows exported:", len(cpi_clean))
else:
    print("\nCPI was NOT exported because validation failed.")