# PresyoPH – Data Collection and Preprocessing

*Member 1 (Data Engineer). Draft written from the code in `data_pipeline/` and its output; for Member 1 to review, correct, and complete (see [section 9](#9-to-confirm-member-1)).*

This document describes how the four PSA datasets were collected, cleaned, validated, and loaded into the `presyoph_db` database that the dashboard and the forecasting models read from. It answers the proposal's first research question ("How can PSA data on CPI, inflation, purchasing power, and household income, expenditure, and savings be collected and preprocessed for analysis?") and is written for the team and as source material for the paper. Every number here comes from the pipeline's own output.

**In short:** the PSA OpenSTAT exports were converted from PSA's wide layout to one row per observation, the unreleased months (September–December 2026) were removed rather than filled in, overlapping years were checked and de-duplicated, and the result was validated at three points: after cleaning, after loading, and between the two. The cleaned data has **no missing values and no duplicates**, and re-running the pipeline from the raw files rebuilds an identical database.

---

## 1. Data sources

All four datasets are public, aggregate PSA statistics from OpenSTAT; none contain individual household records (see the proposal's data privacy section).

| Dataset | Raw file(s) in `datasets/raw/` | PSA table | Coverage used |
|---|---|---|---|
| CPI | `CPI_1.xlsx` (2018–2021), `CPI_2.xlsx` (2022–2023), `CPI_3.xlsx` (2023–2026) | Consumer Price Index for All Income Households by Commodity Group (2018=100) | Jan 2018 – Aug 2026 |
| Inflation | `Inflation_1.xlsx` (2019–2022), `Inflation_2.xlsx` (2023–2026) | Year-on-Year Changes of the Consumer Price Index in Percent by Commodity Group (2018=100) | Jan 2019 – Aug 2026 |
| Purchasing power | `PurchasingPower.xlsx` | Purchasing Power of Peso (2018=100) | Jan 2018 – Aug 2026 |
| FIES | `FIES.csv` | 2023 FIES average income, expenditure and savings by region, province/HUC and per capita income decile ([OpenSTAT](https://openstat.psa.gov.ph/PXWeb/pxweb/en/DB/DB__1E__IE/0081E3AIES0.px)) | 2023 |

CPI and inflation were exported in several files, by year range. The raw files are kept unchanged in the repository; the pipeline only reads them.

## 2. Pipeline overview

```
datasets/raw/            preprocess_*.py         datasets/processed/        load_database.py      presyoph_db
(PSA exports)     ──►    clean + validate   ──►  *_clean.csv         ──►  (after schema.sql) ──►  (MySQL)
                                                       │                                              │
                                              validate_process.py                         validate_database.py
                                                       └──────────── validate_csv_mysql.py ───────────┘
```

| Step | Script | Output |
|---|---|---|
| Clean CPI | `preprocess_cpi.py` | `cpi_clean.csv` |
| Clean inflation | `preprocess_inflation.py` | `inflation_clean.csv` |
| Clean purchasing power | `preprocess_purchasing_power.py` | `purchasing_power_clean.csv` |
| Clean FIES | `preprocess_fies.py` | `fies_clean.csv` |
| Create tables | `database/schema.sql` | empty `presyoph_db` |
| Load | `load_database.py` | populated `presyoph_db` |
| Validate | `validate_process.py`, `validate_database.py`, `validate_csv_mysql.py` | PASS/FAIL report |

Each cleaning script validates its own result and **only writes the CSV if every check passes**.

## 3. Cleaning steps

The proposal lists four preprocessing tasks: data cleaning, handling missing values, standardizing dates and regional labels, and selecting the relevant variables. This section covers them per dataset; sections 4 and 5 cover missing values and standardization across datasets.

### 3.1 CPI, inflation, and purchasing power

These three come in the same OpenSTAT layout: one row per area and commodity group, one column per month, with the year above January only and an annual average column ("Ave") after each December. They are cleaned the same way:

1. **Select the data rows** by position, leaving out the title rows above and PSA's notes below. CPI and inflation have 1,680 data rows per file (120 areas × 14 commodity groups); purchasing power has 120 (one per area, no commodity breakdown).
2. **Fill the area name down**, because PSA prints it only on the first of its 14 rows.
3. **Find the monthly columns**: carry the year forward across its months and drop the annual average columns.
4. **Reshape wide to long**: one row per date, area, and commodity group, with the date built from the year and month (for example "2018 Jan" → 2018-01-01).
5. **Convert values to numbers.** PSA marks months it has not released yet with "..", which become empty and are removed (section 4).
6. **Add the descriptive columns**: `base_year` = 2018 for CPI and purchasing power, `unit` = `percent` for inflation and `peso` for purchasing power.
7. **Combine the files** for CPI and inflation (below), sort, validate, and save.

**Combining the CPI files.** `CPI_2` and `CPI_3` both contain 2023. Before merging, the script compares the two: all **20,160** overlapping values are identical, so 2023 is taken from `CPI_3` and only 2022 from `CPI_2`, with no conflict to resolve. The inflation files do not overlap (2019–2022 and 2023–2026).

| Dataset | Records | Areas | Commodity groups | Months |
|---|---|---|---|---|
| CPI | 174,720 | 120 | 14 | 104 (Jan 2018 – Aug 2026) |
| Inflation | 154,560 | 120 | 14 | 92 (Jan 2019 – Aug 2026) |
| Purchasing power | 12,480 | 120 | – | 104 (Jan 2018 – Aug 2026) |

The 120 areas are the Philippines, 18 regions, the "Areas Outside National Capital Region" group, and 100 provinces and highly urbanized cities. The 14 commodity groups are "0 – All Items" and the 13 COICOP 2018 divisions (01 Food and Non-Alcoholic Beverages through 13 Personal Care and Miscellaneous Goods and Services).

### 3.2 FIES

FIES is a single 2023 table in long format, so it needs selecting and tidying rather than reshaping:

1. **Read the file** as UTF-8, with a fallback to the Windows (cp1252) encoding in case a re-export is saved that way.
2. **Select the four relevant columns** (area, per capita income decile, indicator, value) and drop PSA's source-metadata columns.
3. **Rename** them to `area`, `income_group`, `indicator`, `value`.
4. **Standardize text**: remove the leading dots PSA uses for indentation, collapse repeated spaces, and remove "(in thousand pesos)" from the indicator names, since the unit gets its own column.
5. **Convert values to numbers**, and **add** `year` = 2023 and `unit` = `thousand_pesos`.
6. **Sort, validate, and save.**

The result has **4,554 records**: 138 areas × 11 income groups (all income groups plus the ten deciles) × 3 indicators (average income, expenditure, savings).

**Negative savings are kept.** 27 savings values are below zero, the lowest −10.31 thousand pesos, mostly in the first decile. These are real values (families spending more than their income), not errors, so they were not removed.

## 4. Missing values

The only missing values in the raw data are the months PSA had not yet released: **September–December 2026**, marked "..". They are **removed, not imputed**, because they are future months rather than gaps in the record. After cleaning, every area and commodity group has a complete monthly series (104 months for CPI and purchasing power, 92 for inflation), and no dataset has any missing value. No imputation was needed anywhere.

## 5. Standardization across datasets

- **Dates** are stored as the first day of the month (`YYYY-MM-DD`) in every monthly dataset, so CPI, inflation, and purchasing power line up exactly by date.
- **Area and commodity labels** are identical across CPI, inflation, and purchasing power: all three use PSA's names and the same 120 areas, which the validation checks.
- **PSA's leading dots are kept in the monthly datasets.** They encode the geographic level (two dots for a region or area group, four for a province or city), and the dashboard uses them to tell regions from provinces. The backend removes them for display.
- **FIES uses different area names** (for example "REGION I - ILOCOS REGION" and upper-case province names), and four of its area names carry PSA footnote markers such as "REGION XII - SOCCSKSARGEN2/". These are kept as published in the cleaned file and database; the backend (`backend/sources.py`) removes the markers and maps the FIES names to the CPI names when the dashboard compares them.

## 6. Database

`database/schema.sql` creates six tables in `presyoph_db`:

| Table | Contents | Key |
|---|---|---|
| `areas` | The 120 area names | `area_id` |
| `categories` | The 14 commodity groups | `category_id` |
| `cpi` | Date, area, category, value, base year | unique (date, area, category) |
| `inflation` | Date, area, category, value, unit | unique (date, area, category) |
| `purchasing_power` | Date, area, value, unit, base year | unique (date, area) |
| `fies` | Year, area, income group, indicator, value, unit | unique (year, area, income group, indicator) |

Areas and commodity groups are stored once in lookup tables and referenced by ID from the three monthly tables, with foreign keys enforcing that every reference exists. The unique keys prevent duplicate observations. FIES keeps its own area names (section 5) instead of referencing `areas`.

`load_database.py` fills the lookup tables from the cleaned CPI file, maps names to IDs, stops with an error if any area or category cannot be matched, and inserts the records in batches of 5,000. The database is also exported as `database/presyoph_db.sql`, so the team can set it up with a single import (see the README).

## 7. Validation

Validation happens at three points, and all checks pass on the current data.

**During cleaning** (inside each `preprocess_*.py`): expected row counts, no missing values, no duplicate (date, area, category) observations, the same number of months for every area and category, the expected date range, and, for CPI, the 2023 overlap check in section 3.1.

**After cleaning** (`validate_process.py`, on the four CSVs):

| Check | Result |
|---|---|
| No missing values | PASS |
| No duplicate observations | PASS |
| Value columns are numeric | PASS |
| CPI, inflation and purchasing power have the same areas | PASS |
| CPI and inflation have the same commodity groups | PASS |
| Expected date ranges | PASS |
| Expected record counts | PASS |
| National records present | PASS |
| FIES indicators correct | PASS |

**After loading** (`validate_database.py`, on `presyoph_db`):

| Check | Result |
|---|---|
| Record counts | PASS |
| No duplicate observations | PASS |
| Foreign key references | PASS |
| Expected date ranges | PASS |
| No NULL values | PASS |
| Every monthly table uses all 120 areas (and CPI and inflation all 14 commodity groups) | PASS |

**Between the two** (`validate_csv_mysql.py`): the CPI rows and values in the database match `cpi_clean.csv` (PASS).

**Reproducibility** (checked in October 2026 by Member 2): re-running the four cleaning scripts reproduced the committed CSVs byte for byte, and loading them into a new database with `schema.sql` and `load_database.py` gave the same records and values as `presyoph_db` in all six tables.

## 8. Limitations

1. **Fixed export layout.** The scripts find the data rows by position (for example rows 5–1,684) and expect 120 areas, 14 commodity groups, and the month counts above. A new PSA export with a different layout or more months will fail validation until these are updated. Failing is the intended behaviour: nothing is written when a check fails.
2. **Refreshing the data.** `load_database.py` uses `INSERT IGNORE`, so loading into an existing database skips rows that are already there instead of updating them. If PSA revises past values, drop and recreate the database before loading.
3. **FIES names are matched in the backend, not the pipeline** (section 5), so any other use of the `fies` table has to repeat that mapping.
4. **The CSV-to-database comparison covers CPI only.** The other tables are covered by the record-count and integrity checks, and by the full rebuild comparison in section 7.

## 9. To confirm (Member 1)

These need the author's knowledge and cannot be read from the code:

- [ ] Download date of each raw file, and the exact OpenSTAT table pages for CPI, inflation and purchasing power
- [ ] Why the CPI and inflation tables were exported in several files (export size limit or similar)
- [ ] Any manual steps before the scripts ran (for example renaming files or editing anything in Excel), or confirmation that there were none
- [ ] Whether anything in sections 3–5 differs from the intended method

## 10. Reproducing the data

With MySQL running (see the README):

```
.venv/Scripts/python data_pipeline/preprocess_cpi.py
.venv/Scripts/python data_pipeline/preprocess_inflation.py
.venv/Scripts/python data_pipeline/preprocess_purchasing_power.py
.venv/Scripts/python data_pipeline/preprocess_fies.py
cmd /c "C:\xampp\mysql\bin\mysql -u root < database\schema.sql"
.venv/Scripts/python data_pipeline/load_database.py
.venv/Scripts/python data_pipeline/validate_process.py
.venv/Scripts/python data_pipeline/validate_database.py
.venv/Scripts/python data_pipeline/validate_csv_mysql.py
```

`schema.sql` creates `presyoph_db` if it does not exist. To rebuild from scratch, drop the database first (section 8, item 2).
