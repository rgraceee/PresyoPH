from pathlib import Path
import pandas as pd


# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "datasets" / "raw"
PROCESSED_DIR = BASE_DIR / "datasets" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


INFLATION_1_FILE = RAW_DIR / "Inflation_1.xlsx"
INFLATION_2_FILE = RAW_DIR / "Inflation_2.xlsx"


# ==================================================
# INFLATION_1
# ==================================================

inflation1_raw = pd.read_excel(
    INFLATION_1_FILE,
    header=None
)

inflation1_data = inflation1_raw.iloc[4:1684].copy()

# Fill geographic area labels
inflation1_data[0] = inflation1_data[0].ffill()

# Identify monthly columns
years_inf1 = inflation1_raw.iloc[2].ffill()
periods_inf1 = inflation1_raw.iloc[3]

monthly_columns_inf1 = []

for col in range(2, inflation1_raw.shape[1]):
    year = years_inf1.iloc[col]
    period = periods_inf1.iloc[col]

    if pd.notna(year) and period != "Ave":
        monthly_columns_inf1.append({
            "column": col,
            "year": int(year),
            "month": period
        })


# Convert wide to long format
records_inf1 = []

for item in monthly_columns_inf1:
    col = item["column"]
    year = item["year"]
    month = item["month"]

    date = pd.to_datetime(
        f"{year}-{month}",
        format="%Y-%b"
    )

    for _, row in inflation1_data.iterrows():

        value = pd.to_numeric(
            row[col],
            errors="coerce"
        )

        records_inf1.append({
            "date": date,
            "area": row[0],
            "category": row[1],
            "value": value,
            "unit": "percent"
        })


inflation1_long = pd.DataFrame(records_inf1)


# --------------------------------------------------
# VALIDATE INFLATION_1
# --------------------------------------------------

expected_rows_inf1 = (
    len(inflation1_data)
    * len(monthly_columns_inf1)
)

actual_rows_inf1 = len(inflation1_long)

duplicates_inf1 = inflation1_long.duplicated(
    subset=["date", "area", "category"]
).sum()

coverage_inf1 = (
    inflation1_long
    .groupby(["area", "category"])["date"]
    .nunique()
)

expected_months_inf1 = 48

validation_passed_inf1 = (
    expected_rows_inf1 == actual_rows_inf1
    and inflation1_long["value"].isna().sum() == 0
    and duplicates_inf1 == 0
    and coverage_inf1.min() == expected_months_inf1
    and coverage_inf1.max() == expected_months_inf1
)

print("\n--- INFLATION_1 VALIDATION ---")
print("Observation rows:", len(inflation1_data))
print("Monthly columns:", len(monthly_columns_inf1))
print("Expected rows:", expected_rows_inf1)
print("Actual rows:", actual_rows_inf1)
print("Duplicate observations:", duplicates_inf1)
print("Unique areas:", inflation1_long["area"].nunique())
print("Unique categories:", inflation1_long["category"].nunique())
print(
    "Date range:",
    inflation1_long["date"].min(),
    "to",
    inflation1_long["date"].max()
)
print(
    "Minimum months per area/category:",
    coverage_inf1.min()
)
print(
    "Maximum months per area/category:",
    coverage_inf1.max()
)
print(
    "INFLATION_1 VALIDATION PASSED:",
    validation_passed_inf1
)


# ==================================================
# INFLATION_2
# ==================================================

inflation2_raw = pd.read_excel(
    INFLATION_2_FILE,
    header=None
)

inflation2_data = inflation2_raw.iloc[4:1684].copy()

# Fill geographic area labels
inflation2_data[0] = inflation2_data[0].ffill()

# Identify monthly columns
years_inf2 = inflation2_raw.iloc[2].ffill()
periods_inf2 = inflation2_raw.iloc[3]

monthly_columns_inf2 = []

for col in range(2, inflation2_raw.shape[1]):
    year = years_inf2.iloc[col]
    period = periods_inf2.iloc[col]

    if pd.notna(year) and period != "Ave":
        monthly_columns_inf2.append({
            "column": col,
            "year": int(year),
            "month": period
        })


# Convert wide to long format
records_inf2 = []

for item in monthly_columns_inf2:
    col = item["column"]
    year = item["year"]
    month = item["month"]

    date = pd.to_datetime(
        f"{year}-{month}",
        format="%Y-%b"
    )

    for _, row in inflation2_data.iterrows():

        value = pd.to_numeric(
            row[col],
            errors="coerce"
        )

        records_inf2.append({
            "date": date,
            "area": row[0],
            "category": row[1],
            "value": value,
            "unit": "percent"
        })


inflation2_long = pd.DataFrame(records_inf2)

# Remove unavailable Sep-Dec 2026 observations
inflation2_long = inflation2_long.dropna(
    subset=["value"]
).copy()


# --------------------------------------------------
# VALIDATE INFLATION_2
# --------------------------------------------------

duplicates_inf2 = inflation2_long.duplicated(
    subset=["date", "area", "category"]
).sum()

coverage_inf2 = (
    inflation2_long
    .groupby(["area", "category"])["date"]
    .nunique()
)

expected_months_inf2 = 44

expected_rows_inf2 = (
    len(inflation2_data)
    * expected_months_inf2
)

validation_passed_inf2 = (
    expected_rows_inf2 == len(inflation2_long)
    and inflation2_long["value"].isna().sum() == 0
    and duplicates_inf2 == 0
    and coverage_inf2.min() == expected_months_inf2
    and coverage_inf2.max() == expected_months_inf2
)

print("\n--- INFLATION_2 VALIDATION ---")
print("Observation rows:", len(inflation2_data))
print("Monthly columns found:", len(monthly_columns_inf2))
print(
    "Actual records after removing unavailable values:",
    len(inflation2_long)
)
print("Duplicate observations:", duplicates_inf2)
print("Unique areas:", inflation2_long["area"].nunique())
print("Unique categories:", inflation2_long["category"].nunique())
print(
    "Date range:",
    inflation2_long["date"].min(),
    "to",
    inflation2_long["date"].max()
)
print(
    "Minimum months per area/category:",
    coverage_inf2.min()
)
print(
    "Maximum months per area/category:",
    coverage_inf2.max()
)
print("Expected valid rows:", expected_rows_inf2)
print("Actual valid rows:", len(inflation2_long))
print(
    "INFLATION_2 VALIDATION PASSED:",
    validation_passed_inf2
)


# ==================================================
# MERGE COMPLETE INFLATION DATASET
# ==================================================

inflation_clean = pd.concat(
    [
        inflation1_long,
        inflation2_long
    ],
    ignore_index=True
)

inflation_clean = inflation_clean.sort_values(
    by=["date", "area", "category"]
).reset_index(drop=True)


# --------------------------------------------------
# VALIDATE COMPLETE INFLATION
# --------------------------------------------------

final_duplicates_inf = inflation_clean.duplicated(
    subset=["date", "area", "category"]
).sum()

total_months_inf = inflation_clean["date"].nunique()

final_coverage_inf = (
    inflation_clean
    .groupby(["area", "category"])["date"]
    .nunique()
)

# Jan 2019 through Aug 2026 = 92 months
expected_months_inf = 92

expected_final_rows_inf = (
    inflation_clean["area"].nunique()
    * inflation_clean["category"].nunique()
    * expected_months_inf
)

final_validation_passed_inf = (
    len(inflation_clean) == expected_final_rows_inf
    and total_months_inf == expected_months_inf
    and inflation_clean["value"].isna().sum() == 0
    and final_duplicates_inf == 0
    and final_coverage_inf.min() == expected_months_inf
    and final_coverage_inf.max() == expected_months_inf
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
print("Duplicate observations:", final_duplicates_inf)
print("Total unique months:", total_months_inf)
print(
    "Minimum months per area/category:",
    final_coverage_inf.min()
)
print(
    "Maximum months per area/category:",
    final_coverage_inf.max()
)
print("Expected total rows:", expected_final_rows_inf)
print("Actual total rows:", len(inflation_clean))
print(
    "COMPLETE INFLATION VALIDATION PASSED:",
    final_validation_passed_inf
)


# --------------------------------------------------
# SAVE CLEANED INFLATION
# --------------------------------------------------

if final_validation_passed_inf:
    inflation_output = (
        PROCESSED_DIR / "inflation_clean.csv"
    )

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