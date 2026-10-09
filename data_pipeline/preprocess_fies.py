from pathlib import Path
import pandas as pd


# ==================================================
# PRESYOPH - FIES PREPROCESSING
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "datasets" / "raw"
PROCESSED_DIR = BASE_DIR / "datasets" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

FIES_FILE = RAW_DIR / "FIES.csv"


# --------------------------------------------------
# STEP 1: CHECK RAW FILE
# --------------------------------------------------

print("\n========================================")
print("PRESYOPH - FIES PREPROCESSING")
print("========================================")

if not FIES_FILE.exists():
    raise FileNotFoundError(
        f"Cannot find FIES.csv at:\n{FIES_FILE}"
    )

print("\nFIES.csv -> FOUND")


# --------------------------------------------------
# STEP 2: READ RAW FIES
# --------------------------------------------------

try:
    fies_raw = pd.read_csv(
        FIES_FILE,
        low_memory=False
    )

except UnicodeDecodeError:
    fies_raw = pd.read_csv(
        FIES_FILE,
        encoding="cp1252",
        low_memory=False
    )


print("\n--- RAW FIES ---")
print("Rows:", len(fies_raw))
print("Columns:", len(fies_raw.columns))


# --------------------------------------------------
# STEP 3: SELECT RELEVANT COLUMNS
# --------------------------------------------------

fies_clean = fies_raw[
    [
        "Region, Province, and HUC",
        "Per Capita Income Decile",
        "Indicator",
        "Value (Reported value — see source for units)"
    ]
].copy()


# --------------------------------------------------
# STEP 4: RENAME COLUMNS
# --------------------------------------------------

fies_clean = fies_clean.rename(
    columns={
        "Region, Province, and HUC": "area",
        "Per Capita Income Decile": "income_group",
        "Indicator": "indicator",
        "Value (Reported value — see source for units)": "value"
    }
)


# --------------------------------------------------
# STEP 5: STANDARDIZE AREA NAMES
# --------------------------------------------------

# PSA uses leading dots to show geographic hierarchy.
# Example:
# "..City of Angeles" -> "City of Angeles"
#
# Remove only leading dots, then remove surrounding spaces.

fies_clean["area"] = (
    fies_clean["area"]
    .astype("string")
    .str.replace(r"^\.+", "", regex=True)
    .str.strip()
)


# --------------------------------------------------
# STEP 6: STANDARDIZE INCOME GROUP
# --------------------------------------------------

fies_clean["income_group"] = (
    fies_clean["income_group"]
    .astype("string")
    .str.strip()
    .str.replace(r"\s+", " ", regex=True)
)


# --------------------------------------------------
# STEP 7: STANDARDIZE INDICATOR
# --------------------------------------------------

# Remove the unit text from the indicator because
# the unit will have its own column.

fies_clean["indicator"] = (
    fies_clean["indicator"]
    .astype("string")
    .str.replace(
        r"\s*\(in thousand pesos\)\s*",
        "",
        regex=True
    )
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)


# --------------------------------------------------
# STEP 8: CONVERT VALUE TO NUMERIC
# --------------------------------------------------

fies_clean["value"] = pd.to_numeric(
    fies_clean["value"],
    errors="coerce"
)


# --------------------------------------------------
# STEP 9: ADD YEAR AND UNIT
# --------------------------------------------------

# This dataset is the 2023 FIES snapshot.

fies_clean["year"] = 2023

fies_clean["unit"] = "thousand_pesos"


# --------------------------------------------------
# STEP 10: REORDER COLUMNS
# --------------------------------------------------

fies_clean = fies_clean[
    [
        "year",
        "area",
        "income_group",
        "indicator",
        "value",
        "unit"
    ]
]


# --------------------------------------------------
# STEP 11: SORT DATA
# --------------------------------------------------

fies_clean = fies_clean.sort_values(
    by=[
        "area",
        "income_group",
        "indicator"
    ]
).reset_index(drop=True)


# --------------------------------------------------
# STEP 12: VALIDATE FIES
# --------------------------------------------------

print("\n========================================")
print("FIES VALIDATION")
print("========================================")

print("\nTotal raw rows:")
print(len(fies_raw))

print("\nTotal cleaned rows:")
print(len(fies_clean))


# Missing values
print("\nMissing values:")
print(
    fies_clean.isna().sum()
)


# Duplicate observations
duplicates = fies_clean.duplicated(
    subset=[
        "year",
        "area",
        "income_group",
        "indicator"
    ]
).sum()

print("\nDuplicate observations:")
print(duplicates)


# Areas
print("\nUnique areas:")
print(
    fies_clean["area"].nunique()
)


# Income groups
print("\nIncome groups:")

income_groups = sorted(
    fies_clean["income_group"]
    .dropna()
    .unique()
)

for group in income_groups:
    print("-", group)


# Indicators
print("\nIndicators:")

indicator_counts = (
    fies_clean["indicator"]
    .value_counts()
)

print(indicator_counts)


# --------------------------------------------------
# STEP 13: CHECK EXPECTED INDICATORS
# --------------------------------------------------

expected_indicators = {
    "Average Income",
    "Average Expenditure",
    "Average Savings"
}

actual_indicators = set(
    fies_clean["indicator"]
    .dropna()
    .unique()
)

indicators_correct = (
    actual_indicators == expected_indicators
)

print(
    "\nExpected indicators present:",
    indicators_correct
)


# --------------------------------------------------
# STEP 14: CHECK YEAR
# --------------------------------------------------

years_correct = (
    set(fies_clean["year"].unique()) == {2023}
)

print(
    "Year correct:",
    years_correct
)


# --------------------------------------------------
# STEP 15: CHECK UNIT
# --------------------------------------------------

units_correct = (
    set(fies_clean["unit"].unique())
    == {"thousand_pesos"}
)

print(
    "Unit correct:",
    units_correct
)


# --------------------------------------------------
# STEP 16: CHECK VALUE RANGE
# --------------------------------------------------

print("\nMinimum value:")
print(fies_clean["value"].min())

print("\nMaximum value:")
print(fies_clean["value"].max())


# --------------------------------------------------
# STEP 17: FINAL VALIDATION
# --------------------------------------------------

validation_passed = (
    len(fies_clean) == len(fies_raw)
    and fies_clean.isna().sum().sum() == 0
    and duplicates == 0
    and indicators_correct
    and years_correct
    and units_correct
)


print(
    "\nFIES VALIDATION PASSED:",
    validation_passed
)


# --------------------------------------------------
# STEP 18: PREVIEW CLEANED DATA
# --------------------------------------------------

print("\n--- CLEANED FIES PREVIEW ---")

print(
    fies_clean
    .head(20)
    .to_string(index=False)
)


# --------------------------------------------------
# STEP 19: EXPORT
# --------------------------------------------------

if validation_passed:

    output_file = (
        PROCESSED_DIR / "fies_clean.csv"
    )

    fies_clean.to_csv(
        output_file,
        index=False
    )

    print("\n========================================")
    print("FIES EXPORT")
    print("========================================")

    print(
        "FIES preprocessing completed successfully."
    )

    print(
        "Saved to:",
        output_file
    )

    print(
        "Rows exported:",
        len(fies_clean)
    )

else:

    print(
        "\nFIES was NOT exported because "
        "validation failed."
    )