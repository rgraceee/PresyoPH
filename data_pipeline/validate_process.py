from pathlib import Path
import pandas as pd


# ==================================================
# PRESYOPH - PROCESSED DATA VALIDATION
# ==================================================
# Purpose:
# Perform final cross-dataset quality checks before
# loading the cleaned datasets into SQLite.
#
# IMPORTANT:
# This script DOES NOT modify any processed dataset.
# ==================================================


# --------------------------------------------------
# STEP 1: PROJECT PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "datasets" / "processed"

CPI_FILE = PROCESSED_DIR / "cpi_clean.csv"
INFLATION_FILE = PROCESSED_DIR / "inflation_clean.csv"
PURCHASING_POWER_FILE = (
    PROCESSED_DIR / "purchasing_power_clean.csv"
)
FIES_FILE = PROCESSED_DIR / "fies_clean.csv"


# --------------------------------------------------
# STEP 2: CHECK FILES
# --------------------------------------------------

files = {
    "CPI": CPI_FILE,
    "Inflation": INFLATION_FILE,
    "Purchasing Power": PURCHASING_POWER_FILE,
    "FIES": FIES_FILE
}

print("\n========================================")
print("PRESYOPH - PROCESSED DATA VALIDATION")
print("========================================")

all_files_found = True

for name, file in files.items():

    exists = file.exists()

    print(
        f"{name}:",
        "FOUND" if exists else "NOT FOUND"
    )

    if not exists:
        all_files_found = False


if not all_files_found:
    raise FileNotFoundError(
        "One or more processed datasets are missing."
    )


# --------------------------------------------------
# STEP 3: LOAD PROCESSED DATASETS
# --------------------------------------------------

cpi = pd.read_csv(
    CPI_FILE,
    parse_dates=["date"]
)

inflation = pd.read_csv(
    INFLATION_FILE,
    parse_dates=["date"]
)

purchasing_power = pd.read_csv(
    PURCHASING_POWER_FILE,
    parse_dates=["date"]
)

fies = pd.read_csv(
    FIES_FILE
)


print("\nAll processed datasets loaded successfully.")


# --------------------------------------------------
# STEP 4: BASIC DATASET SUMMARY
# --------------------------------------------------

print("\n========================================")
print("DATASET SUMMARY")
print("========================================")

print("\nCPI")
print("Rows:", len(cpi))
print("Columns:", list(cpi.columns))

print("\nInflation")
print("Rows:", len(inflation))
print("Columns:", list(inflation.columns))

print("\nPurchasing Power")
print("Rows:", len(purchasing_power))
print("Columns:", list(purchasing_power.columns))

print("\nFIES")
print("Rows:", len(fies))
print("Columns:", list(fies.columns))


# --------------------------------------------------
# STEP 5: MISSING VALUE CHECK
# --------------------------------------------------

print("\n========================================")
print("MISSING VALUE CHECK")
print("========================================")

datasets = {
    "CPI": cpi,
    "Inflation": inflation,
    "Purchasing Power": purchasing_power,
    "FIES": fies
}

missing_pass = True

for name, df in datasets.items():

    missing = int(df.isna().sum().sum())

    print(
        f"{name}: {missing} missing values"
    )

    if missing != 0:
        missing_pass = False


# --------------------------------------------------
# STEP 6: DUPLICATE OBSERVATION CHECK
# --------------------------------------------------

print("\n========================================")
print("DUPLICATE CHECK")
print("========================================")

cpi_duplicates = cpi.duplicated(
    subset=["date", "area", "category"]
).sum()

inflation_duplicates = inflation.duplicated(
    subset=["date", "area", "category"]
).sum()

pp_duplicates = purchasing_power.duplicated(
    subset=["date", "area"]
).sum()

fies_duplicates = fies.duplicated(
    subset=[
        "year",
        "area",
        "income_group",
        "indicator"
    ]
).sum()


print("CPI duplicates:", cpi_duplicates)
print("Inflation duplicates:", inflation_duplicates)
print("Purchasing Power duplicates:", pp_duplicates)
print("FIES duplicates:", fies_duplicates)


duplicates_pass = (
    cpi_duplicates == 0
    and inflation_duplicates == 0
    and pp_duplicates == 0
    and fies_duplicates == 0
)


# --------------------------------------------------
# STEP 7: NUMERIC VALUE CHECK
# --------------------------------------------------

print("\n========================================")
print("NUMERIC VALUE CHECK")
print("========================================")

numeric_pass = True

for name, df in datasets.items():

    is_numeric = pd.api.types.is_numeric_dtype(
        df["value"]
    )

    print(
        f"{name} value column numeric:",
        is_numeric
    )

    if not is_numeric:
        numeric_pass = False


# --------------------------------------------------
# STEP 8: AREA CONSISTENCY
# CPI vs INFLATION vs PURCHASING POWER
# --------------------------------------------------

print("\n========================================")
print("AREA CONSISTENCY CHECK")
print("========================================")

cpi_areas = set(
    cpi["area"].dropna().unique()
)

inflation_areas = set(
    inflation["area"].dropna().unique()
)

pp_areas = set(
    purchasing_power["area"].dropna().unique()
)


print("CPI areas:", len(cpi_areas))
print("Inflation areas:", len(inflation_areas))
print("Purchasing Power areas:", len(pp_areas))


cpi_inflation_match = (
    cpi_areas == inflation_areas
)

cpi_pp_match = (
    cpi_areas == pp_areas
)

inflation_pp_match = (
    inflation_areas == pp_areas
)


print(
    "\nCPI vs Inflation areas match:",
    cpi_inflation_match
)

print(
    "CPI vs Purchasing Power areas match:",
    cpi_pp_match
)

print(
    "Inflation vs Purchasing Power areas match:",
    inflation_pp_match
)


# Show differences if any exist

if not cpi_inflation_match:

    print("\nAreas only in CPI:")
    print(
        sorted(cpi_areas - inflation_areas)
    )

    print("\nAreas only in Inflation:")
    print(
        sorted(inflation_areas - cpi_areas)
    )


if not cpi_pp_match:

    print("\nAreas only in CPI:")
    print(
        sorted(cpi_areas - pp_areas)
    )

    print("\nAreas only in Purchasing Power:")
    print(
        sorted(pp_areas - cpi_areas)
    )


area_pass = (
    cpi_inflation_match
    and cpi_pp_match
    and inflation_pp_match
)


# --------------------------------------------------
# STEP 9: CPI / INFLATION CATEGORY CONSISTENCY
# --------------------------------------------------

print("\n========================================")
print("CATEGORY CONSISTENCY CHECK")
print("========================================")

cpi_categories = set(
    cpi["category"].dropna().unique()
)

inflation_categories = set(
    inflation["category"].dropna().unique()
)


print(
    "CPI categories:",
    len(cpi_categories)
)

print(
    "Inflation categories:",
    len(inflation_categories)
)


category_match = (
    cpi_categories == inflation_categories
)

print(
    "\nCPI vs Inflation categories match:",
    category_match
)


if not category_match:

    print("\nCategories only in CPI:")
    print(
        sorted(
            cpi_categories - inflation_categories
        )
    )

    print("\nCategories only in Inflation:")
    print(
        sorted(
            inflation_categories - cpi_categories
        )
    )


# --------------------------------------------------
# STEP 10: DATE RANGE CHECK
# --------------------------------------------------

print("\n========================================")
print("DATE RANGE CHECK")
print("========================================")

print(
    "CPI:",
    cpi["date"].min(),
    "to",
    cpi["date"].max()
)

print(
    "Inflation:",
    inflation["date"].min(),
    "to",
    inflation["date"].max()
)

print(
    "Purchasing Power:",
    purchasing_power["date"].min(),
    "to",
    purchasing_power["date"].max()
)

print(
    "FIES year(s):",
    sorted(fies["year"].unique())
)


date_pass = (
    cpi["date"].min()
    == pd.Timestamp("2018-01-01")

    and cpi["date"].max()
    == pd.Timestamp("2026-08-01")

    and inflation["date"].min()
    == pd.Timestamp("2019-01-01")

    and inflation["date"].max()
    == pd.Timestamp("2026-08-01")

    and purchasing_power["date"].min()
    == pd.Timestamp("2018-01-01")

    and purchasing_power["date"].max()
    == pd.Timestamp("2026-08-01")

    and set(fies["year"].unique())
    == {2023}
)

print(
    "\nExpected date coverage correct:",
    date_pass
)


# --------------------------------------------------
# STEP 11: EXPECTED RECORD COUNTS
# --------------------------------------------------

print("\n========================================")
print("RECORD COUNT CHECK")
print("========================================")

expected_cpi = 174720
expected_inflation = 154560
expected_pp = 12480


print(
    "CPI:",
    len(cpi),
    "| Expected:",
    expected_cpi
)

print(
    "Inflation:",
    len(inflation),
    "| Expected:",
    expected_inflation
)

print(
    "Purchasing Power:",
    len(purchasing_power),
    "| Expected:",
    expected_pp
)

print(
    "FIES:",
    len(fies)
)


record_count_pass = (
    len(cpi) == expected_cpi
    and len(inflation) == expected_inflation
    and len(purchasing_power) == expected_pp
)


# --------------------------------------------------
# STEP 12: NATIONAL RECORD CHECK
# --------------------------------------------------

print("\n========================================")
print("NATIONAL RECORD CHECK")
print("========================================")

national_label = "PHILIPPINES"

cpi_national = (
    national_label in cpi_areas
)

inflation_national = (
    national_label in inflation_areas
)

pp_national = (
    national_label in pp_areas
)


print(
    "CPI has PHILIPPINES:",
    cpi_national
)

print(
    "Inflation has PHILIPPINES:",
    inflation_national
)

print(
    "Purchasing Power has PHILIPPINES:",
    pp_national
)


national_pass = (
    cpi_national
    and inflation_national
    and pp_national
)


# --------------------------------------------------
# STEP 13: FIES AREA COMPARISON
# --------------------------------------------------

print("\n========================================")
print("FIES AREA COMPARISON")
print("========================================")

fies_areas = set(
    fies["area"].dropna().unique()
)

print(
    "FIES unique areas:",
    len(fies_areas)
)


fies_matching_areas = (
    fies_areas & cpi_areas
)

fies_only_areas = (
    fies_areas - cpi_areas
)

cpi_only_areas = (
    cpi_areas - fies_areas
)


print(
    "FIES areas matching CPI exactly:",
    len(fies_matching_areas)
)

print(
    "FIES areas not matching CPI exactly:",
    len(fies_only_areas)
)


if len(fies_only_areas) > 0:

    print("\nFIES-only/non-matching area names:")

    for area in sorted(fies_only_areas):
        print("-", area)


print(
    "\nCPI areas not present exactly in FIES:",
    len(cpi_only_areas)
)


# IMPORTANT:
# FIES does not have to contain exactly the same
# geographic coverage as CPI.
#
# Therefore, differences here are reported for
# inspection but do NOT automatically fail the
# overall validation.


# --------------------------------------------------
# STEP 14: FIES INDICATOR CHECK
# --------------------------------------------------

print("\n========================================")
print("FIES INDICATOR CHECK")
print("========================================")

expected_fies_indicators = {
    "Average Income",
    "Average Expenditure",
    "Average Savings"
}

actual_fies_indicators = set(
    fies["indicator"]
    .dropna()
    .unique()
)

print(
    "Indicators:",
    sorted(actual_fies_indicators)
)

fies_indicator_pass = (
    actual_fies_indicators
    == expected_fies_indicators
)

print(
    "Expected FIES indicators present:",
    fies_indicator_pass
)


# --------------------------------------------------
# STEP 15: FINAL VALIDATION SUMMARY
# --------------------------------------------------

print("\n========================================")
print("FINAL VALIDATION SUMMARY")
print("========================================")

checks = {
    "No missing values": missing_pass,
    "No duplicate observations": duplicates_pass,
    "Value columns are numeric": numeric_pass,
    "Main dataset areas match": area_pass,
    "CPI/Inflation categories match": category_match,
    "Expected date ranges": date_pass,
    "Expected record counts": record_count_pass,
    "National records present": national_pass,
    "FIES indicators correct": fies_indicator_pass
}


for check, passed in checks.items():

    status = "PASS" if passed else "FAIL"

    print(
        f"{check}: {status}"
    )


overall_pass = all(
    checks.values()
)


print("\n----------------------------------------")

print(
    "OVERALL PROCESSED DATA VALIDATION:",
    "PASSED" if overall_pass else "FAILED"
)

print("----------------------------------------")


if overall_pass:

    print(
        "\nThe processed datasets are ready "
        "for database loading."
    )

else:

    print(
        "\nOne or more checks failed. "
        "Review the results above before "
        "loading the data into SQLite."
    )