from pathlib import Path

import pandas as pd
import mysql.connector


# ==========================================
# PROJECT PATH
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "datasets" / "processed"

CPI_FILE = PROCESSED_DIR / "cpi_clean.csv"


# ==========================================
# CONNECT TO MYSQL
# ==========================================

connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="presyoph_db"
)


print("\n========================================")
print("PRESYOPH CPI CSV ↔ MYSQL DIAGNOSIS")
print("========================================")


# ==========================================
# LOAD CPI FROM CSV
# ==========================================

print("\nLoading CPI CSV...")

cpi_csv = pd.read_csv(
    CPI_FILE,
    parse_dates=["date"]
)

print("CPI CSV loaded.")
print("Rows:", len(cpi_csv))


# ==========================================
# LOAD CPI FROM MYSQL
# ==========================================

print("\nLoading CPI from MySQL...")

cpi_sql = pd.read_sql(
    """
    SELECT
        c.date,
        a.area_name AS area,
        cat.category_name AS category,
        c.value,
        c.base_year
    FROM cpi c
    INNER JOIN areas a
        ON c.area_id = a.area_id
    INNER JOIN categories cat
        ON c.category_id = cat.category_id
    """,
    connection
)

print("CPI MySQL data loaded.")
print("Rows:", len(cpi_sql))


# ==========================================
# STANDARDIZE DATA TYPES
# ==========================================

cpi_csv["date"] = pd.to_datetime(
    cpi_csv["date"]
)

cpi_sql["date"] = pd.to_datetime(
    cpi_sql["date"]
)


cpi_csv["area"] = (
    cpi_csv["area"]
    .astype(str)
    .str.strip()
)

cpi_sql["area"] = (
    cpi_sql["area"]
    .astype(str)
    .str.strip()
)


cpi_csv["category"] = (
    cpi_csv["category"]
    .astype(str)
    .str.strip()
)

cpi_sql["category"] = (
    cpi_sql["category"]
    .astype(str)
    .str.strip()
)


cpi_csv["value"] = (
    cpi_csv["value"]
    .astype(float)
)

cpi_sql["value"] = (
    cpi_sql["value"]
    .astype(float)
)


cpi_csv["base_year"] = (
    cpi_csv["base_year"]
    .astype(int)
)

cpi_sql["base_year"] = (
    cpi_sql["base_year"]
    .astype(int)
)


# ==========================================
# SORT BOTH DATASETS
# ==========================================

sort_columns = [
    "date",
    "area",
    "category"
]

cpi_csv = (
    cpi_csv
    .sort_values(sort_columns)
    .reset_index(drop=True)
)

cpi_sql = (
    cpi_sql
    .sort_values(sort_columns)
    .reset_index(drop=True)
)


# ==========================================
# SHOW DATA TYPES
# ==========================================

print("\n========================================")
print("DATA TYPE CHECK")
print("========================================")

print("\nCSV data types:")
print(cpi_csv.dtypes)

print("\nMySQL data types:")
print(cpi_sql.dtypes)


# ==========================================
# CHECK ROW COUNTS
# ==========================================

print("\n========================================")
print("ROW COUNT CHECK")
print("========================================")

print(
    "CSV rows:",
    len(cpi_csv)
)

print(
    "MySQL rows:",
    len(cpi_sql)
)

if len(cpi_csv) == len(cpi_sql):
    print("Row count: PASS")
else:
    print("Row count: FAIL")


# ==========================================
# COMPARE EACH COLUMN
# ==========================================

print("\n========================================")
print("COLUMN-BY-COLUMN COMPARISON")
print("========================================")


# DATE

date_diff = (
    cpi_csv["date"]
    != cpi_sql["date"]
)

print(
    "date:",
    int(date_diff.sum()),
    "differences"
)


# AREA

area_diff = (
    cpi_csv["area"]
    != cpi_sql["area"]
)

print(
    "area:",
    int(area_diff.sum()),
    "differences"
)


# CATEGORY

category_diff = (
    cpi_csv["category"]
    != cpi_sql["category"]
)

print(
    "category:",
    int(category_diff.sum()),
    "differences"
)


# VALUE
# Small tolerance is used for decimal/float comparison.

value_difference = (
    cpi_csv["value"]
    - cpi_sql["value"]
).abs()

value_diff = (
    value_difference > 0.000001
)

print(
    "value:",
    int(value_diff.sum()),
    "differences"
)


# BASE YEAR

base_year_diff = (
    cpi_csv["base_year"]
    != cpi_sql["base_year"]
)

print(
    "base_year:",
    int(base_year_diff.sum()),
    "differences"
)


# ==========================================
# SHOW FIRST VALUE DIFFERENCES
# ==========================================

if value_diff.sum() > 0:

    print("\n========================================")
    print("FIRST 10 VALUE DIFFERENCES")
    print("========================================")

    value_comparison = pd.DataFrame({
        "date": cpi_csv.loc[
            value_diff,
            "date"
        ],

        "area": cpi_csv.loc[
            value_diff,
            "area"
        ],

        "category": cpi_csv.loc[
            value_diff,
            "category"
        ],

        "CSV_value": cpi_csv.loc[
            value_diff,
            "value"
        ],

        "MySQL_value": cpi_sql.loc[
            value_diff,
            "value"
        ],

        "difference": value_difference.loc[
            value_diff
        ]
    })

    print(
        value_comparison.head(10).to_string(
            index=False
        )
    )


# ==========================================
# SHOW TEXT DIFFERENCES IF ANY
# ==========================================

if area_diff.sum() > 0:

    print("\nFirst 5 AREA differences:")

    area_comparison = pd.DataFrame({
        "CSV": cpi_csv.loc[
            area_diff,
            "area"
        ],
        "MySQL": cpi_sql.loc[
            area_diff,
            "area"
        ]
    })

    print(
        area_comparison.head(5).to_string()
    )


if category_diff.sum() > 0:

    print("\nFirst 5 CATEGORY differences:")

    category_comparison = pd.DataFrame({
        "CSV": cpi_csv.loc[
            category_diff,
            "category"
        ],
        "MySQL": cpi_sql.loc[
            category_diff,
            "category"
        ]
    })

    print(
        category_comparison.head(5).to_string()
    )


# ==========================================
# FINAL CPI RESULT
# ==========================================

print("\n========================================")
print("CPI DIAGNOSIS RESULT")
print("========================================")

all_match = (
    len(cpi_csv) == len(cpi_sql)
    and date_diff.sum() == 0
    and area_diff.sum() == 0
    and category_diff.sum() == 0
    and value_diff.sum() == 0
    and base_year_diff.sum() == 0
)


if all_match:

    print("CPI CSV ↔ MySQL: PASS")
    print(
        "All CPI records and values match."
    )

else:

    print("CPI CSV ↔ MySQL: FAIL")
    print(
        "The output above shows which "
        "column has differences."
    )


# ==========================================
# CLOSE DATABASE CONNECTION
# ==========================================

connection.close()

print("\nDatabase connection closed.")