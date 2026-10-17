# PresyoPH

Dashboard for Philippine CPI, inflation, purchasing power, and FIES data,
with CPI forecasts. Built with Streamlit; data is served from a MySQL
database (XAMPP).

## Setup

Requires Python 3.13 and [XAMPP](https://www.apachefriends.org/) (MySQL/MariaDB).

### 1. Python environment

Windows:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### 2. Database

1. Open the XAMPP Control Panel and start **MySQL**.
2. Import `database/presyoph_db.sql`. It creates the `presyoph_db` database
   and loads the data. In phpMyAdmin (http://localhost/phpmyadmin), open the
   **Import** tab without selecting a database. From a terminal:

   ```powershell
   cmd /c "C:\xampp\mysql\bin\mysql -u root < database\presyoph_db.sql"
   ```

   To re-import, drop the old database first (`DROP DATABASE presyoph_db;`),
   since the dump does not overwrite existing tables.
3. Check the import. These row counts should match:

   | Table              | Rows    |
   |--------------------|---------|
   | `cpi`              | 174,720 |
   | `inflation`        | 154,560 |
   | `purchasing_power` | 12,480  |
   | `fies`             | 4,554   |
   | `areas`            | 120     |
   | `categories`       | 14      |

The backend uses XAMPP's default login (`root`, no password, `localhost:3306`).
If yours is different, set these environment variables before running the app:
`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.

## Running

MySQL must be running before you start the app or the tests.

```powershell
.venv\Scripts\python -m streamlit run app/streamlit_app.py
```

The dashboard opens at http://localhost:8501. Data is cached at startup, so
restart Streamlit after you re-import the database.

Run the tests:

```powershell
.venv\Scripts\python -m pytest
```

## Project layout

| Path             | Contents                                              |
|------------------|-------------------------------------------------------|
| `app/`           | Streamlit dashboard (pages, chart components, theme) |
| `backend/`       | Data access layer used by the dashboard               |
| `modeling/`      | CPI forecasting models                                |
| `data_pipeline/` | ETL scripts: preprocessing, loading, validation      |
| `database/`      | MySQL schema and data dump                            |
| `datasets/`      | Cleaned datasets and model outputs                    |
| `tests/`         | pytest suite                                          |
