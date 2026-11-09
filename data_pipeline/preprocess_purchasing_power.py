"""Preprocess the raw PurchasingPower.xlsx file into a cleaned CSV."""

from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "datasets" / "raw"
PROCESSED_DIR = BASE_DIR / "datasets" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

PURCHASING_POWER_FILE = RAW_DIR / "PurchasingPower.xlsx"


purchasing_power_raw = pd.read_excel(
    PURCHASING_POWER_FILE,
    header=None
)

purchasing_power_data = (
    purchasing_power_raw.iloc[4:124].copy()
)

years_ppp = purchasing_power_raw.iloc[2].ffill()
periods_ppp = purchasing_power_raw.iloc[3]

monthly_columns_ppp = []

for col in range(
    2,
    purchasing_power_raw.shape[1]
):
    year = years_ppp.iloc[col]
    period = periods_ppp.iloc[col]

    if pd.notna(year) and period != "Ave":
        monthly_columns_ppp.append({
            "column": col,
            "year": int(year),
            "month": period
        })


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


purchasing_power_long = (
    purchasing_power_long
    .dropna(subset=["value"])
    .copy()
)


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
    "\nRow count correct:",
    expected_rows_ppp
    == len(purchasing_power_long)
)

print(
    "\nPURCHASING POWER VALIDATION PASSED:",
    validation_passed_ppp
)


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
