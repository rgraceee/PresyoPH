import mysql.connector


# ==========================================
# PRESYOPH DATABASE VALIDATION
# ==========================================

connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="presyoph_db"
)

cursor = connection.cursor()

print("\n========================================")
print("PRESYOPH DATABASE VALIDATION")
print("========================================")


# ==========================================
# 1. RECORD COUNT CHECK
# ==========================================

print("\n========================================")
print("RECORD COUNT CHECK")
print("========================================")

expected_counts = {
    "areas": 120,
    "categories": 14,
    "cpi": 174720,
    "inflation": 154560,
    "purchasing_power": 12480,
    "fies": 4554
}

count_pass = True

for table, expected in expected_counts.items():

    cursor.execute(
        f"SELECT COUNT(*) FROM {table}"
    )

    actual = cursor.fetchone()[0]

    status = (
        "PASS"
        if actual == expected
        else "FAIL"
    )

    print(
        f"{table}: {actual} "
        f"| Expected: {expected} "
        f"| {status}"
    )

    if actual != expected:
        count_pass = False


# ==========================================
# 2. CPI DUPLICATE CHECK
# ==========================================

print("\n========================================")
print("DUPLICATE CHECK")
print("========================================")

cursor.execute("""
    SELECT COUNT(*)
    FROM (
        SELECT
            date,
            area_id,
            category_id,
            COUNT(*) AS total
        FROM cpi
        GROUP BY
            date,
            area_id,
            category_id
        HAVING COUNT(*) > 1
    ) AS duplicates
""")

cpi_duplicates = cursor.fetchone()[0]


# ==========================================
# 3. INFLATION DUPLICATE CHECK
# ==========================================

cursor.execute("""
    SELECT COUNT(*)
    FROM (
        SELECT
            date,
            area_id,
            category_id,
            COUNT(*) AS total
        FROM inflation
        GROUP BY
            date,
            area_id,
            category_id
        HAVING COUNT(*) > 1
    ) AS duplicates
""")

inflation_duplicates = cursor.fetchone()[0]


# ==========================================
# 4. PURCHASING POWER DUPLICATE CHECK
# ==========================================

cursor.execute("""
    SELECT COUNT(*)
    FROM (
        SELECT
            date,
            area_id,
            COUNT(*) AS total
        FROM purchasing_power
        GROUP BY
            date,
            area_id
        HAVING COUNT(*) > 1
    ) AS duplicates
""")

pp_duplicates = cursor.fetchone()[0]


# ==========================================
# 5. FIES DUPLICATE CHECK
# ==========================================

cursor.execute("""
    SELECT COUNT(*)
    FROM (
        SELECT
            year,
            area,
            income_group,
            indicator,
            COUNT(*) AS total
        FROM fies
        GROUP BY
            year,
            area,
            income_group,
            indicator
        HAVING COUNT(*) > 1
    ) AS duplicates
""")

fies_duplicates = cursor.fetchone()[0]


print("CPI duplicates:", cpi_duplicates)
print("Inflation duplicates:", inflation_duplicates)
print(
    "Purchasing Power duplicates:",
    pp_duplicates
)
print("FIES duplicates:", fies_duplicates)

duplicate_pass = (
    cpi_duplicates == 0
    and inflation_duplicates == 0
    and pp_duplicates == 0
    and fies_duplicates == 0
)


# ==========================================
# 6. FOREIGN KEY CHECK
# ==========================================

print("\n========================================")
print("FOREIGN KEY REFERENCE CHECK")
print("========================================")


# CPI area references

cursor.execute("""
    SELECT COUNT(*)
    FROM cpi c
    LEFT JOIN areas a
        ON c.area_id = a.area_id
    WHERE a.area_id IS NULL
""")

cpi_invalid_areas = cursor.fetchone()[0]


# CPI category references

cursor.execute("""
    SELECT COUNT(*)
    FROM cpi c
    LEFT JOIN categories cat
        ON c.category_id = cat.category_id
    WHERE cat.category_id IS NULL
""")

cpi_invalid_categories = cursor.fetchone()[0]


# Inflation area references

cursor.execute("""
    SELECT COUNT(*)
    FROM inflation i
    LEFT JOIN areas a
        ON i.area_id = a.area_id
    WHERE a.area_id IS NULL
""")

inflation_invalid_areas = cursor.fetchone()[0]


# Inflation category references

cursor.execute("""
    SELECT COUNT(*)
    FROM inflation i
    LEFT JOIN categories cat
        ON i.category_id = cat.category_id
    WHERE cat.category_id IS NULL
""")

inflation_invalid_categories = cursor.fetchone()[0]


# Purchasing Power area references

cursor.execute("""
    SELECT COUNT(*)
    FROM purchasing_power p
    LEFT JOIN areas a
        ON p.area_id = a.area_id
    WHERE a.area_id IS NULL
""")

pp_invalid_areas = cursor.fetchone()[0]


print(
    "CPI invalid area references:",
    cpi_invalid_areas
)

print(
    "CPI invalid category references:",
    cpi_invalid_categories
)

print(
    "Inflation invalid area references:",
    inflation_invalid_areas
)

print(
    "Inflation invalid category references:",
    inflation_invalid_categories
)

print(
    "Purchasing Power invalid area references:",
    pp_invalid_areas
)


foreign_key_pass = (
    cpi_invalid_areas == 0
    and cpi_invalid_categories == 0
    and inflation_invalid_areas == 0
    and inflation_invalid_categories == 0
    and pp_invalid_areas == 0
)


# ==========================================
# 7. DATE RANGE CHECK
# ==========================================

print("\n========================================")
print("DATE RANGE CHECK")
print("========================================")

cursor.execute(
    "SELECT MIN(date), MAX(date) FROM cpi"
)
cpi_min, cpi_max = cursor.fetchone()

cursor.execute(
    "SELECT MIN(date), MAX(date) FROM inflation"
)
inflation_min, inflation_max = cursor.fetchone()

cursor.execute(
    "SELECT MIN(date), MAX(date) "
    "FROM purchasing_power"
)
pp_min, pp_max = cursor.fetchone()

cursor.execute(
    "SELECT MIN(year), MAX(year) FROM fies"
)
fies_min, fies_max = cursor.fetchone()


print(
    "CPI:",
    cpi_min,
    "to",
    cpi_max
)

print(
    "Inflation:",
    inflation_min,
    "to",
    inflation_max
)

print(
    "Purchasing Power:",
    pp_min,
    "to",
    pp_max
)

print(
    "FIES:",
    fies_min,
    "to",
    fies_max
)


date_pass = (
    str(cpi_min) == "2018-01-01"
    and str(cpi_max) == "2026-08-01"
    and str(inflation_min) == "2019-01-01"
    and str(inflation_max) == "2026-08-01"
    and str(pp_min) == "2018-01-01"
    and str(pp_max) == "2026-08-01"
    and fies_min == 2023
    and fies_max == 2023
)


# ==========================================
# 8. NULL VALUE CHECK
# ==========================================

print("\n========================================")
print("NULL VALUE CHECK")
print("========================================")

null_queries = {
    "CPI": """
        SELECT COUNT(*)
        FROM cpi
        WHERE
            date IS NULL
            OR area_id IS NULL
            OR category_id IS NULL
            OR value IS NULL
            OR base_year IS NULL
    """,

    "Inflation": """
        SELECT COUNT(*)
        FROM inflation
        WHERE
            date IS NULL
            OR area_id IS NULL
            OR category_id IS NULL
            OR value IS NULL
            OR unit IS NULL
    """,

    "Purchasing Power": """
        SELECT COUNT(*)
        FROM purchasing_power
        WHERE
            date IS NULL
            OR area_id IS NULL
            OR value IS NULL
            OR unit IS NULL
            OR base_year IS NULL
    """,

    "FIES": """
        SELECT COUNT(*)
        FROM fies
        WHERE
            year IS NULL
            OR area IS NULL
            OR income_group IS NULL
            OR indicator IS NULL
            OR value IS NULL
            OR unit IS NULL
    """
}

null_pass = True

for name, query in null_queries.items():

    cursor.execute(query)
    count = cursor.fetchone()[0]

    print(
        f"{name} NULL records:",
        count
    )

    if count != 0:
        null_pass = False


# ==========================================
# 9. LOOKUP TABLE CHECK
# ==========================================

print("\n========================================")
print("LOOKUP TABLE CHECK")
print("========================================")

cursor.execute("""
    SELECT COUNT(DISTINCT area_id)
    FROM cpi
""")
cpi_area_count = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(DISTINCT category_id)
    FROM cpi
""")
cpi_category_count = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(DISTINCT area_id)
    FROM inflation
""")
inflation_area_count = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(DISTINCT category_id)
    FROM inflation
""")
inflation_category_count = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(DISTINCT area_id)
    FROM purchasing_power
""")
pp_area_count = cursor.fetchone()[0]


print(
    "CPI areas used:",
    cpi_area_count
)

print(
    "CPI categories used:",
    cpi_category_count
)

print(
    "Inflation areas used:",
    inflation_area_count
)

print(
    "Inflation categories used:",
    inflation_category_count
)

print(
    "Purchasing Power areas used:",
    pp_area_count
)


lookup_pass = (
    cpi_area_count == 120
    and cpi_category_count == 14
    and inflation_area_count == 120
    and inflation_category_count == 14
    and pp_area_count == 120
)


# ==========================================
# 10. FINAL VALIDATION SUMMARY
# ==========================================

print("\n========================================")
print("FINAL DATABASE VALIDATION SUMMARY")
print("========================================")

checks = {
    "Record counts": count_pass,
    "No duplicate observations": duplicate_pass,
    "Foreign key references": foreign_key_pass,
    "Expected date ranges": date_pass,
    "No NULL values": null_pass,
    "Lookup table usage": lookup_pass
}

for check, passed in checks.items():

    status = (
        "PASS"
        if passed
        else "FAIL"
    )

    print(
        f"{check}: {status}"
    )


overall_pass = all(checks.values())


print("\n----------------------------------------")

print(
    "OVERALL DATABASE VALIDATION:",
    "PASSED"
    if overall_pass
    else "FAILED"
)

print("----------------------------------------")


if overall_pass:

    print(
        "\nPresyoPH database passed all "
        "integrity checks."
    )

else:

    print(
        "\nOne or more database checks failed. "
        "Review the results above."
    )


# ==========================================
# CLOSE CONNECTION
# ==========================================

cursor.close()
connection.close()

print("\nDatabase connection closed.")