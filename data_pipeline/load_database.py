from pathlib import Path

import pandas as pd
import mysql.connector


# ==========================================
# PROJECT PATHS
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "datasets" / "processed"

CPI_FILE = PROCESSED_DIR / "cpi_clean.csv"
INFLATION_FILE = PROCESSED_DIR / "inflation_clean.csv"
PURCHASING_POWER_FILE = PROCESSED_DIR / "purchasing_power_clean.csv"
FIES_FILE = PROCESSED_DIR / "fies_clean.csv"


# ==========================================
# CONNECT TO MYSQL
# ==========================================

connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="presyoph_db"
)

cursor = connection.cursor()

print("Successfully connected to PresyoPH MySQL database.")


# ==========================================
# LOAD CLEANED CPI DATA
# ==========================================

cpi = pd.read_csv(CPI_FILE)

print("\nCPI dataset loaded.")
print("Rows:", len(cpi))


# ==========================================
# INSERT AREAS
# ==========================================

areas = sorted(cpi["area"].unique())

area_sql = """
INSERT IGNORE INTO areas (area_name)
VALUES (%s)
"""

cursor.executemany(
    area_sql,
    [(area,) for area in areas]
)

connection.commit()

print("\nAreas loaded successfully.")
print("Expected areas:", len(areas))


# ==========================================
# INSERT CATEGORIES
# ==========================================

categories = sorted(cpi["category"].unique())

category_sql = """
INSERT IGNORE INTO categories (category_name)
VALUES (%s)
"""

cursor.executemany(
    category_sql,
    [(category,) for category in categories]
)

connection.commit()

print("\nCategories loaded successfully.")
print("Expected categories:", len(categories))

# ==========================================
# GET AREA AND CATEGORY IDS
# ==========================================

cursor.execute("SELECT area_id, area_name FROM areas")
area_map = {
    area_name: area_id
    for area_id, area_name in cursor.fetchall()
}

cursor.execute(
    "SELECT category_id, category_name FROM categories"
)
category_map = {
    category_name: category_id
    for category_id, category_name in cursor.fetchall()
}

print("\nArea and category ID mappings created.")


# ==========================================
# PREPARE CPI RECORDS
# ==========================================

cpi["area_id"] = cpi["area"].map(area_map)
cpi["category_id"] = cpi["category"].map(category_map)

if cpi["area_id"].isna().any():
    raise ValueError(
        "Some CPI areas could not be matched to the areas table."
    )

if cpi["category_id"].isna().any():
    raise ValueError(
        "Some CPI categories could not be matched "
        "to the categories table."
    )


cpi_records = [
    (
        date,
        int(area_id),
        int(category_id),
        float(value),
        int(base_year)
    )
    for date, area_id, category_id, value, base_year
    in cpi[
        [
            "date",
            "area_id",
            "category_id",
            "value",
            "base_year"
        ]
    ].itertuples(index=False, name=None)
]


# ==========================================
# INSERT CPI DATA
# ==========================================

cpi_sql = """
INSERT IGNORE INTO cpi
    (date, area_id, category_id, value, base_year)
VALUES
    (%s, %s, %s, %s, %s)
"""

BATCH_SIZE = 5000

print("\nLoading CPI data into MySQL...")

for start in range(0, len(cpi_records), BATCH_SIZE):

    batch = cpi_records[
        start:start + BATCH_SIZE
    ]

    cursor.executemany(
        cpi_sql,
        batch
    )

    connection.commit()

    loaded = min(
        start + BATCH_SIZE,
        len(cpi_records)
    )

    print(
        f"CPI progress: {loaded}/{len(cpi_records)}"
    )

print("\nCPI data loaded successfully.")


# ==========================================
# LOAD CLEANED INFLATION DATA
# ==========================================

inflation = pd.read_csv(INFLATION_FILE)

print("\nInflation dataset loaded.")
print("Rows:", len(inflation))


# ==========================================
# MAP AREA AND CATEGORY IDS
# ==========================================

inflation["area_id"] = inflation["area"].map(area_map)
inflation["category_id"] = inflation["category"].map(category_map)

if inflation["area_id"].isna().any():
    raise ValueError(
        "Some Inflation areas could not be matched "
        "to the areas table."
    )

if inflation["category_id"].isna().any():
    raise ValueError(
        "Some Inflation categories could not be matched "
        "to the categories table."
    )

print("All Inflation areas and categories matched successfully.")


# ==========================================
# PREPARE INFLATION RECORDS
# ==========================================

inflation_records = [
    (
        date,
        int(area_id),
        int(category_id),
        float(value),
        unit
    )
    for date, area_id, category_id, value, unit
    in inflation[
        [
            "date",
            "area_id",
            "category_id",
            "value",
            "unit"
        ]
    ].itertuples(index=False, name=None)
]


# ==========================================
# INSERT INFLATION DATA
# ==========================================

inflation_sql = """
INSERT IGNORE INTO inflation
    (date, area_id, category_id, value, unit)
VALUES
    (%s, %s, %s, %s, %s)
"""

print("\nLoading Inflation data into MySQL...")

for start in range(
    0,
    len(inflation_records),
    BATCH_SIZE
):

    batch = inflation_records[
        start:start + BATCH_SIZE
    ]

    cursor.executemany(
        inflation_sql,
        batch
    )

    connection.commit()

    loaded = min(
        start + BATCH_SIZE,
        len(inflation_records)
    )

    print(
        f"Inflation progress: "
        f"{loaded}/{len(inflation_records)}"
    )

print("\nInflation data loaded successfully.")

# ==========================================
# LOAD CLEANED PURCHASING POWER DATA
# ==========================================

purchasing_power = pd.read_csv(PURCHASING_POWER_FILE)

print("\nPurchasing Power dataset loaded.")
print("Rows:", len(purchasing_power))


# ==========================================
# MAP AREA IDS
# ==========================================

purchasing_power["area_id"] = purchasing_power["area"].map(area_map)

if purchasing_power["area_id"].isna().any():
    raise ValueError(
        "Some Purchasing Power areas could not be matched "
        "to the areas table."
    )

print("All Purchasing Power areas matched successfully.")


# ==========================================
# PREPARE PURCHASING POWER RECORDS
# ==========================================

purchasing_power_records = [
    (
        date,
        int(area_id),
        float(value),
        unit,
        int(base_year)
    )
    for date, area_id, value, unit, base_year
    in purchasing_power[
        [
            "date",
            "area_id",
            "value",
            "unit",
            "base_year"
        ]
    ].itertuples(index=False, name=None)
]


# ==========================================
# INSERT PURCHASING POWER DATA
# ==========================================

purchasing_power_sql = """
INSERT IGNORE INTO purchasing_power
    (date, area_id, value, unit, base_year)
VALUES
    (%s, %s, %s, %s, %s)
"""

print("\nLoading Purchasing Power data into MySQL...")

for start in range(
    0,
    len(purchasing_power_records),
    BATCH_SIZE
):

    batch = purchasing_power_records[
        start:start + BATCH_SIZE
    ]

    cursor.executemany(
        purchasing_power_sql,
        batch
    )

    connection.commit()

    loaded = min(
        start + BATCH_SIZE,
        len(purchasing_power_records)
    )

    print(
        f"Purchasing Power progress: "
        f"{loaded}/{len(purchasing_power_records)}"
    )

print("\nPurchasing Power data loaded successfully.")

# ==========================================
# LOAD CLEANED FIES DATA
# ==========================================

fies = pd.read_csv(FIES_FILE)

print("\nFIES dataset loaded.")
print("Rows:", len(fies))


# ==========================================
# PREPARE FIES RECORDS
# ==========================================

fies_records = [
    (
        int(year),
        area,
        income_group,
        indicator,
        float(value),
        unit
    )
    for year, area, income_group, indicator, value, unit
    in fies[
        [
            "year",
            "area",
            "income_group",
            "indicator",
            "value",
            "unit"
        ]
    ].itertuples(index=False, name=None)
]


# ==========================================
# INSERT FIES DATA
# ==========================================

fies_sql = """
INSERT IGNORE INTO fies
    (year, area, income_group, indicator, value, unit)
VALUES
    (%s, %s, %s, %s, %s, %s)
"""

print("\nLoading FIES data into MySQL...")

for start in range(
    0,
    len(fies_records),
    BATCH_SIZE
):

    batch = fies_records[
        start:start + BATCH_SIZE
    ]

    cursor.executemany(
        fies_sql,
        batch
    )

    connection.commit()

    loaded = min(
        start + BATCH_SIZE,
        len(fies_records)
    )

    print(
        f"FIES progress: "
        f"{loaded}/{len(fies_records)}"
    )

print("\nFIES data loaded successfully.")

# ==========================================
# VERIFY DATABASE COUNTS
# ==========================================

cursor.execute("SELECT COUNT(*) FROM areas")
area_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM categories")
category_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM cpi")
cpi_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM inflation")
inflation_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM purchasing_power")
purchasing_power_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM fies")
fies_count = cursor.fetchone()[0]

print("\n========================================")
print("DATABASE CHECK")
print("========================================")

print("Areas in database:", area_count)
print("Categories in database:", category_count)
print("CPI records in database:", cpi_count)
print("Inflation records in database:", inflation_count)
print("Purchasing Power records in database:", purchasing_power_count)
print("FIES records in database:", fies_count)

# ==========================================
# CLOSE CONNECTION
# ==========================================

cursor.close()
connection.close()

print("\nDatabase connection closed.")

