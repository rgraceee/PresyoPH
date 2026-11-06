"""PresyoPH database validation.

Connects to presyoph_db and runs integrity checks:
  1. Record counts
  2. Duplicate observations
  3. Foreign key references
  4. Date ranges
  5. NULL values
  6. Lookup table usage

Prints PASS/FAIL for each check and an overall result.
"""

import mysql.connector


# --------------------------------------------------
# CONNECT
# --------------------------------------------------

connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="presyoph_db",
)
cursor = connection.cursor()


def count_rows(sql):
    """Run a COUNT query and return the integer result."""
    cursor.execute(sql)
    return cursor.fetchone()[0]


def section(title):
    """Print a section header."""
    print(f"\n{title}")
    print("=" * len(title))


def check_result(label, passed):
    """Print PASS/FAIL for one check."""
    print(f"{label}: {'PASS' if passed else 'FAIL'}")
    return passed


# ==================================================
# 1. RECORD COUNT CHECK
# ==================================================

section("PRESYOPH DATABASE VALIDATION")
section("1. RECORD COUNT CHECK")

expected_counts = {
    "areas": 120,
    "categories": 14,
    "cpi": 174720,
    "inflation": 154560,
    "purchasing_power": 12480,
    "fies": 4554,
}

count_pass = True
for table, expected in expected_counts.items():
    actual = count_rows(f"SELECT COUNT(*) FROM {table}")
    status = "PASS" if actual == expected else "FAIL"
    print(f"{table}: {actual} | Expected: {expected} | {status}")
    if actual != expected:
        count_pass = False

# ==================================================
# 2-5. DUPLICATE CHECKS
# ==================================================

section("2. DUPLICATE CHECK")

dup_sql = {
    "cpi": """
        SELECT COUNT(*) FROM (
            SELECT date, area_id, category_id, COUNT(*) AS total
            FROM cpi GROUP BY date, area_id, category_id HAVING COUNT(*) > 1
        ) AS duplicates
    """,
    "inflation": """
        SELECT COUNT(*) FROM (
            SELECT date, area_id, category_id, COUNT(*) AS total
            FROM inflation GROUP BY date, area_id, category_id HAVING COUNT(*) > 1
        ) AS duplicates
    """,
    "purchasing_power": """
        SELECT COUNT(*) FROM (
            SELECT date, area_id, COUNT(*) AS total
            FROM purchasing_power GROUP BY date, area_id HAVING COUNT(*) > 1
        ) AS duplicates
    """,
    "fies": """
        SELECT COUNT(*) FROM (
            SELECT year, area, income_group, indicator, COUNT(*) AS total
            FROM fies GROUP BY year, area, income_group, indicator HAVING COUNT(*) > 1
        ) AS duplicates
    """,
}

dup_results = {name: count_rows(sql) for name, sql in dup_sql.items()}
for name, cnt in dup_results.items():
    print(f"{name.capitalize()} duplicates: {cnt}")

duplicate_pass = all(c == 0 for c in dup_results.values())

# ==================================================
# 6. FOREIGN KEY CHECK
# ==================================================

section("6. FOREIGN KEY REFERENCE CHECK")

fk_sql = {
    "CPI invalid area references": """
        SELECT COUNT(*) FROM cpi c
        LEFT JOIN areas a ON c.area_id = a.area_id WHERE a.area_id IS NULL
    """,
    "CPI invalid category references": """
        SELECT COUNT(*) FROM cpi c
        LEFT JOIN categories cat ON c.category_id = cat.category_id WHERE cat.category_id IS NULL
    """,
    "Inflation invalid area references": """
        SELECT COUNT(*) FROM inflation i
        LEFT JOIN areas a ON i.area_id = a.area_id WHERE a.area_id IS NULL
    """,
    "Inflation invalid category references": """
        SELECT COUNT(*) FROM inflation i
        LEFT JOIN categories cat ON i.category_id = cat.category_id WHERE cat.category_id IS NULL
    """,
    "Purchasing Power invalid area references": """
        SELECT COUNT(*) FROM purchasing_power p
        LEFT JOIN areas a ON p.area_id = a.area_id WHERE a.area_id IS NULL
    """,
}

fk_results = {label: count_rows(sql) for label, sql in fk_sql.items()}
for label, cnt in fk_results.items():
    print(f"{label}: {cnt}")

foreign_key_pass = all(c == 0 for c in fk_results.values())

# ==================================================
# 7. DATE RANGE CHECK
# ==================================================

section("7. DATE RANGE CHECK")

cpi_min, cpi_max = count_rows("SELECT MIN(date) FROM cpi"), None
cursor.execute("SELECT MIN(date), MAX(date) FROM cpi")
cpi_min, cpi_max = cursor.fetchone()
cursor.execute("SELECT MIN(date), MAX(date) FROM inflation")
inflation_min, inflation_max = cursor.fetchone()
cursor.execute("SELECT MIN(date), MAX(date) FROM purchasing_power")
pp_min, pp_max = cursor.fetchone()
cursor.execute("SELECT MIN(year), MAX(year) FROM fies")
fies_min, fies_max = cursor.fetchone()

print("CPI:", cpi_min, "to", cpi_max)
print("Inflation:", inflation_min, "to", inflation_max)
print("Purchasing Power:", pp_min, "to", pp_max)
print("FIES:", fies_min, "to", fies_max)

date_pass = (
    str(cpi_min) == "2018-01-01" and str(cpi_max) == "2026-08-01"
    and str(inflation_min) == "2019-01-01" and str(inflation_max) == "2026-08-01"
    and str(pp_min) == "2018-01-01" and str(pp_max) == "2026-08-01"
    and fies_min == 2023 and fies_max == 2023
)

# ==================================================
# 8. NULL VALUE CHECK
# ==================================================

section("8. NULL VALUE CHECK")

null_queries = {
    "CPI": """
        SELECT COUNT(*) FROM cpi
        WHERE date IS NULL OR area_id IS NULL OR category_id IS NULL
           OR value IS NULL OR base_year IS NULL
    """,
    "Inflation": """
        SELECT COUNT(*) FROM inflation
        WHERE date IS NULL OR area_id IS NULL OR category_id IS NULL
           OR value IS NULL OR unit IS NULL
    """,
    "Purchasing Power": """
        SELECT COUNT(*) FROM purchasing_power
        WHERE date IS NULL OR area_id IS NULL OR value IS NULL
           OR unit IS NULL OR base_year IS NULL
    """,
    "FIES": """
        SELECT COUNT(*) FROM fies
        WHERE year IS NULL OR area IS NULL OR income_group IS NULL
           OR indicator IS NULL OR value IS NULL OR unit IS NULL
    """,
}

null_pass = True
for name, query in null_queries.items():
    count = count_rows(query)
    print(f"{name} NULL records: {count}")
    if count != 0:
        null_pass = False

# ==================================================
# 9. LOOKUP TABLE CHECK
# ==================================================

section("9. LOOKUP TABLE CHECK")

lookup_sql = {
    "CPI areas used": "SELECT COUNT(DISTINCT area_id) FROM cpi",
    "CPI categories used": "SELECT COUNT(DISTINCT category_id) FROM cpi",
    "Inflation areas used": "SELECT COUNT(DISTINCT area_id) FROM inflation",
    "Inflation categories used": "SELECT COUNT(DISTINCT category_id) FROM inflation",
    "Purchasing Power areas used": "SELECT COUNT(DISTINCT area_id) FROM purchasing_power",
}

lookup_results = {label: count_rows(sql) for label, sql in lookup_sql.items()}
for label, cnt in lookup_results.items():
    print(f"{label}: {cnt}")

lookup_pass = (
    lookup_results["CPI areas used"] == 120
    and lookup_results["CPI categories used"] == 14
    and lookup_results["Inflation areas used"] == 120
    and lookup_results["Inflation categories used"] == 14
    and lookup_results["Purchasing Power areas used"] == 120
)

# ==================================================
# 10. FINAL VALIDATION SUMMARY
# ==================================================

section("10. FINAL VALIDATION SUMMARY")

checks = {
    "Record counts": count_pass,
    "No duplicate observations": duplicate_pass,
    "Foreign key references": foreign_key_pass,
    "Expected date ranges": date_pass,
    "No NULL values": null_pass,
    "Lookup table usage": lookup_pass,
}

overall_pass = True
for check, passed in checks.items():
    print(f"{check}: {'PASS' if passed else 'FAIL'}")
    if not passed:
        overall_pass = False

print("\n----------------------------------------")
print("OVERALL DATABASE VALIDATION:", "PASSED" if overall_pass else "FAILED")
print("----------------------------------------")

if overall_pass:
    print("\nPresyoPH database passed all integrity checks.")
else:
    print("\nOne or more database checks failed. Review the results above.")

cursor.close()
connection.close()
print("\nDatabase connection closed.")
