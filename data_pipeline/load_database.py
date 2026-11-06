"""Loads cleaned CSVs from datasets/processed/ into presyoph_db.

Run database/schema.sql first. Inserts use INSERT IGNORE, so rows that
already exist are skipped, not updated. To refresh the data, drop and
recreate the database, then load.

Uses the same connection settings as backend/sources.py (XAMPP defaults:
localhost:3306, root, no password).
"""

import os
from pathlib import Path

import pandas as pd
import mysql.connector


# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "datasets" / "processed"

CPI_FILE = PROCESSED_DIR / "cpi_clean.csv"
INFLATION_FILE = PROCESSED_DIR / "inflation_clean.csv"
PURCHASING_POWER_FILE = PROCESSED_DIR / "purchasing_power_clean.csv"
FIES_FILE = PROCESSED_DIR / "fies_clean.csv"

BATCH_SIZE = 5000


# --------------------------------------------------
# CONNECT TO MYSQL
# --------------------------------------------------

connection = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "presyoph_db"),
)

cursor = connection.cursor()

print("Successfully connected to PresyoPH MySQL database.")


# --------------------------------------------------
# REUSABLE LOADERS
# --------------------------------------------------

def load_lookup_table(df_column, table_name, column_name, label):
    """Insert unique values from a dataframe column into a lookup table.

    Parameters
    ----------
    df_column : pandas.Series
        Values to insert.
    table_name : str
        Database table name.
    column_name : str
        Column to insert into.
    label : str
        Human-readable name for progress messages.
    """
    values = sorted(df_column.unique())
    sql = f"INSERT IGNORE INTO {table_name} ({column_name}) VALUES (%s)"
    cursor.executemany(sql, [(v,) for v in values])
    connection.commit()
    print(f"\n{label} loaded successfully.")
    print(f"Expected {label.lower()}:", len(values))
    return values


def load_data_records(records, sql, table_label):
    """Insert rows in batches and print progress.

    Parameters
    ----------
    records : list of tuples
        Row data to insert.
    sql : str
        INSERT statement with %s placeholders.
    table_label : str
        Human-readable name for progress messages.
    """
    print(f"\nLoading {table_label} data into MySQL...")
    for start in range(0, len(records), BATCH_SIZE):
        batch = records[start:start + BATCH_SIZE]
        cursor.executemany(sql, batch)
        connection.commit()
        loaded = min(start + BATCH_SIZE, len(records))
        print(f"{table_label} progress: {loaded}/{len(records)}")
    print(f"\n{table_label} data loaded successfully.")


# --------------------------------------------------
# AREAS AND CATEGORIES (from CPI data)
# --------------------------------------------------

cpi = pd.read_csv(CPI_FILE)
print("\nCPI dataset loaded.")
print("Rows:", len(cpi))

areas = load_lookup_table(cpi["area"], "areas", "area_name", "Areas")
categories = load_lookup_table(cpi["category"], "categories", "category_name", "Categories")

cursor.execute("SELECT area_id, area_name FROM areas")
area_map = {name: aid for aid, name in cursor.fetchall()}

cursor.execute("SELECT category_id, category_name FROM categories")
category_map = {name: cid for cid, name in cursor.fetchall()}

print("\nArea and category ID mappings created.")


# --------------------------------------------------
# CPI DATA
# --------------------------------------------------

cpi["area_id"] = cpi["area"].map(area_map)
cpi["category_id"] = cpi["category"].map(category_map)

if cpi["area_id"].isna().any():
    raise ValueError("Some CPI areas could not be matched to the areas table.")
if cpi["category_id"].isna().any():
    raise ValueError("Some CPI categories could not be matched to the categories table.")

cpi_records = [
    (date, int(aid), int(cid), float(val), int(by))
    for date, aid, cid, val, by
    in cpi[["date", "area_id", "category_id", "value", "base_year"]].itertuples(index=False, name=None)
]

cpi_sql = """
INSERT IGNORE INTO cpi
    (date, area_id, category_id, value, base_year)
VALUES (%s, %s, %s, %s, %s)
"""
load_data_records(cpi_records, cpi_sql, "CPI")


# --------------------------------------------------
# INFLATION DATA
# --------------------------------------------------

inflation = pd.read_csv(INFLATION_FILE)
print("\nInflation dataset loaded.")
print("Rows:", len(inflation))

inflation["area_id"] = inflation["area"].map(area_map)
inflation["category_id"] = inflation["category"].map(category_map)

if inflation["area_id"].isna().any():
    raise ValueError("Some Inflation areas could not be matched to the areas table.")
if inflation["category_id"].isna().any():
    raise ValueError("Some Inflation categories could not be matched to the categories table.")

print("All Inflation areas and categories matched successfully.")

inflation_records = [
    (date, int(aid), int(cid), float(val), unit)
    for date, aid, cid, val, unit
    in inflation[["date", "area_id", "category_id", "value", "unit"]].itertuples(index=False, name=None)
]

inflation_sql = """
INSERT IGNORE INTO inflation
    (date, area_id, category_id, value, unit)
VALUES (%s, %s, %s, %s, %s)
"""
load_data_records(inflation_records, inflation_sql, "Inflation")


# --------------------------------------------------
# PURCHASING POWER DATA
# --------------------------------------------------

purchasing_power = pd.read_csv(PURCHASING_POWER_FILE)
print("\nPurchasing Power dataset loaded.")
print("Rows:", len(purchasing_power))

purchasing_power["area_id"] = purchasing_power["area"].map(area_map)
if purchasing_power["area_id"].isna().any():
    raise ValueError("Some Purchasing Power areas could not be matched to the areas table.")

print("All Purchasing Power areas matched successfully.")

pp_records = [
    (date, int(aid), float(val), unit, int(by))
    for date, aid, val, unit, by
    in purchasing_power[["date", "area_id", "value", "unit", "base_year"]].itertuples(index=False, name=None)
]

pp_sql = """
INSERT IGNORE INTO purchasing_power
    (date, area_id, value, unit, base_year)
VALUES (%s, %s, %s, %s, %s)
"""
load_data_records(pp_records, pp_sql, "Purchasing Power")


# --------------------------------------------------
# FIES DATA
# --------------------------------------------------

fies = pd.read_csv(FIES_FILE)
print("\nFIES dataset loaded.")
print("Rows:", len(fies))

fies_records = [
    (int(year), area, group, ind, float(val), unit)
    for year, area, group, ind, val, unit
    in fies[["year", "area", "income_group", "indicator", "value", "unit"]].itertuples(index=False, name=None)
]

fies_sql = """
INSERT IGNORE INTO fies
    (year, area, income_group, indicator, value, unit)
VALUES (%s, %s, %s, %s, %s, %s)
"""
load_data_records(fies_records, fies_sql, "FIES")


# --------------------------------------------------
# VERIFY DATABASE COUNTS
# --------------------------------------------------

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


# --------------------------------------------------
# CLOSE CONNECTION
# --------------------------------------------------

cursor.close()
connection.close()
print("\nDatabase connection closed.")
