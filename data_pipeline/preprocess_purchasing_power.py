"""
================================================================================
FILE: data_pipeline/preprocess_purchasing_power.py
================================================================================
WHAT THIS FILE IS FOR:
----------------------
Preprocesses the raw PurchasingPower.xlsx file from datasets/raw/ into a
cleaned CSV at datasets/processed/purchasing_power_clean.csv.

Purchasing power of the peso is a monthly time series (Jan 2018 - Aug 2026)
showing how much a peso can buy compared with the 2018 base year. It has no
commodity breakdown (only "all items").

Steps:
  1. Read the raw Excel file (no header row)
  2. Isolate observation rows (120 geographic areas)
  3. Identify monthly columns (year + period, skipping "Ave")
  4. Convert wide format to long format (date, area, value, unit, base_year)
  5. Remove unavailable observations (Sep-Dec 2026)
  6. Validate: row counts, missing values, duplicates, coverage
  7. Export to purchasing_power_clean.csv if validation passes

================================================================================
HOW IT CONNECTS TO OTHER FILES:
-------------------------------
- datasets/raw/PurchasingPower.xlsx: Input file (raw PSA purchasing power data).
- datasets/processed/purchasing_power_clean.csv: Output file.
- data_pipeline/load_database.py: Loads into MySQL purchasing_power table.
- backend/sources.py: Reads from MySQL via price_table() and series().
- backend/data.py: Provides get_purchasing_power(), get_series().

================================================================================
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


PURCHASING_POWER_FILE = (
    RAW_DIR / "PurchasingPower.xlsx"
)


# ==================================================
# LOAD PURCHASING POWER DATA
# ==================================================

purchasing_power_raw = pd.read_excel(
    PURCHASING_POWER_FILE,
    header=None
)


# --------------------------------------------------
# ISOLATE OBSERVATION ROWS
# --------------------------------------------------

# Python indexes 4-123 = 120 geographic areas
purchasing_power_data = (
    purchasing_power_raw.iloc[4:124].copy()
)


# --------------------------------------------------
# IDENTIFY MONTHLY COLUMNS
# --------------------------------------------------

years_ppp = purchasing_power_raw.iloc[2].ffill()
periods_ppp = purchasing_power_raw.iloc[3]

monthly_columns_ppp = []

for col in range(
    2,
    purchasing_power_raw.shape[1]
):
    year = years_ppp.iloc[col]
    period = periods_ppp.iloc[col]

    # Keep Jan-Dec only; exclude annual averages
    if pd.notna(year) and period != "Ave":
        monthly_columns_ppp.append({
            "column": col,
            "year": int(year),
            "month": period
        })


# --------------------------------------------------
# CONVERT WIDE FORMAT TO LONG FORMAT
# --------------------------------------------------

records_ppp = []

for item in monthly_columns_ppp:
    col = item["column"]
    year = item["year"]
    month = item["month"]

    date = pd.to_datetime(
        f"{year}-{month}",
        format="%Y-%b"
    )

    for _, row in purchasing_power_data.iterrows():

        # PSA ".." values become NaN
        value = pd.to_numeric(
            row[col],
            errors="coerce"
        )

        records_ppp.append({
            "date": date,
            "area": row[0],
            "value": value,
            "unit": "peso",
            "base_year": 2018
        })


purchasing_power_long = pd.DataFrame(
    records_ppp
)


# --------------------------------------------------
# REMOVE UNAVAILABLE OBSERVATIONS
# --------------------------------------------------

# Sep-Dec 2026 are unavailable in the PSA source.
purchasing_power_long = (
    purchasing_power_long
    .dropna(subset=["value"])
    .copy()
)


# --------------------------------------------------
# VALIDATE PURCHASING POWER
# --------------------------------------------------

duplicates_ppp = (
    purchasing_power_long
    .duplicated(
        subset=["date", "area"]
    )
    .sum()
)

coverage_ppp = (
    purchasing_power_long
    .groupby("area")["date"]
    .nunique()
)

# Jan 2018 through Aug 2026:
# 2018-2025 = 96 months
# 2026 Jan-Aug = 8 months
# Total = 104 months
expected_months_ppp = 104

expected_rows_ppp = (
    len(purchasing_power_data)
    * expected_months_ppp
)

validation_passed_ppp = (
    len(purchasing_power_data) == 120
    and len(purchasing_power_long) == expected_rows_ppp
    and purchasing_power_long["value"].isna().sum() == 0
    and duplicates_ppp == 0
    and purchasing_power_long["area"].nunique() == 120
    and coverage_ppp.min() == expected_months_ppp
    and coverage_ppp.max() == expected_months_ppp
)


print("\n--- PURCHASING POWER VALIDATION ---")

print(
    "Observation rows:",
    len(purchasing_power_data)
)

print(
    "Monthly columns found:",
    len(monthly_columns_ppp)
)

print(
    "Actual records after removing unavailable values:",
    len(purchasing_power_long)
)

print("\nMissing values:")
print(
    purchasing_power_long.isna().sum()
)

print(
    "\nDuplicate observations:",
    duplicates_ppp
)

print(
    "\nUnique areas:",
    purchasing_power_long["area"].nunique()
)

print("\nDate range:")
print(
    purchasing_power_long["date"].min(),
    "to",
    purchasing_power_long["date"].max()
)

print(
    "\nMinimum months per area:",
    coverage_ppp.min()
)

print(
    "Maximum months per area:",
    coverage_ppp.max()
)

print(
    "\nExpected valid rows:",
    expected_rows_ppp
)

print(
    "Actual valid rows:",
    len(purchasing_power_long)
)

print(
    "Row count correct:",
    expected_rows_ppp
    == len(purchasing_power_long)
)

print(
    "\nPURCHASING POWER VALIDATION PASSED:",
    validation_passed_ppp
)


# --------------------------------------------------
# SAVE CLEANED PURCHASING POWER
# --------------------------------------------------

if validation_passed_ppp:

    purchasing_power_output = (
        PROCESSED_DIR
        / "purchasing_power_clean.csv"
    )

    purchasing_power_long.to_csv(
        purchasing_power_output,
        index=False,
        date_format="%Y-%m-%d"
    )

    print(
        "\nPurchasing Power preprocessing "
        "completed successfully."
    )
    print(
        "Saved to:",
        purchasing_power_output
    )
    print(
        "Rows exported:",
        len(purchasing_power_long)
    )

else:
    print(
        "\nPurchasing Power was NOT exported "
        "because validation failed."
    )
