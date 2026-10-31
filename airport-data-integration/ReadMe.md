# Airport Data Integration Module

## 1. Project Overview

The Airport Data Integration module is responsible for collecting, cleaning, processing, generating, validating, and storing airport operational data for the Airport Operations Coordination Engine.

This module integrates master airport and runway datasets with synthetic operational data such as flights, gates, gate bookings, staff, and crew rosters.

The processed data is stored in an SQLite database and made available for other modules of the application.

## 2. Objectives

- Clean and standardize airport and runway datasets.
- Maintain raw and processed datasets separately.
- Generate synthetic airport operational data.
- Maintain database relationships and referential integrity.
- Load airport and operational records into SQLite.
- Prevent duplicate records during repeated data loading.
- Validate data quality and operational constraints.
- Provide automated tests for data integration functionality.

## 3. Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.13 | Core programming language |
| Pandas | CSV data cleaning and processing |
| SQLite | Relational database storage |
| Pytest | Automated testing |
| Git and GitHub | Version control and collaboration |
| VS Code | Development environment |

## 4. Project Structure

```text
airport-data-integration/
│
├── data/
│   ├── raw/
│   │   ├── airports.csv
│   │   ├── airports_selected.csv
│   │   └── runways.csv
│   │
│   ├── processed/
│   │   ├── airports.csv
│   │   └── runways.csv
│   │
│   └── synthetic/
│       ├── flights.csv
│       ├── gates.csv
│       ├── gate_bookings.csv
│       ├── staff.csv
│       └── crew_rosters.csv
│
├── database/
│   ├── __init__.py
│   ├── db.py
│   ├── init_db.py
│   └── schema.sql
│
├── scripts/
│   ├── clean_airports.py
│   ├── generate_synthetic_data.py
│   ├── load_airports.py
│   ├── load_runways.py
│   ├── load_gates.py
│   ├── load_flights.py
│   ├── load_gate_bookings.py
│   ├── load_staff.py
│   ├── load_crew_rosters.py
│   ├── load_all_data.py
│   ├── validate_synthetic_data.py
│   └── verify_database.py
│
├── tests/
│   ├── test_airport_data.py
│   ├── test_database_loaders.py
│   └── test_synthetic_data.py
│
├── check_db.py
├── requirements.txt
├── README.md
└── .gitignore
```

**Note:** The SQLite database file is generated locally and is excluded from GitHub using `.gitignore`.

## 5. Data Sources

### Master Data

The module uses airport and runway datasets as its master data sources.

- `airports.csv` – Original airport records.
- `airports_selected.csv` – Selected target airports.
- `runways.csv` – Original runway records.

### Processed Data

The cleaning script processes the raw datasets and generates standardized CSV files.

- `processed/airports.csv`
- `processed/runways.csv`

### Synthetic Operational Data

The synthetic data generator creates:

- Flights
- Gates
- Gate bookings
- Airport staff
- Crew rosters

Generated operational records include an `is_synthetic` flag to identify synthetic records.

## 6. Installation and Setup

### Prerequisites

- Python 3.13
- Git
- Visual Studio Code

### Step 1: Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
```

Navigate into the project directory:

```bash
cd airport-data-integration
```

### Step 2: Create a virtual environment

```bash
python -m venv .venv
```

### Step 3: Activate the virtual environment

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 4: Install dependencies

```bash
python -m pip install -r requirements.txt
```

## 7. Data Integration Workflow

Follow the execution sequence below.

### Step 1: Clean Airport and Runway Data

```bash
python scripts/clean_airports.py
```

This script reads the raw datasets, cleans and standardizes the records, and generates processed airport and runway CSV files.

### Step 2: Generate Synthetic Operational Data

```bash
python scripts/generate_synthetic_data.py
```

This generates synthetic flights, gates, gate bookings, staff, and crew rosters.

The generator uses a fixed default random seed to support reproducible data generation.

### Step 3: Validate Synthetic Data

```bash
python scripts/validate_synthetic_data.py
```

This checks:

- Required CSV columns.
- Missing values and data types.
- Unique identifiers.
- Airport and flight references.
- Booking time validity.
- Gate allocation overlaps.
- Crew scheduling conflicts.
- Synthetic data flags.

### Step 4: Initialize the SQLite Database

```bash
python database/init_db.py
```

This creates the SQLite database and initializes its tables using `database/schema.sql`.

### Step 5: Load Data into the Database

First, perform a dry run:

```bash
python scripts/load_all_data.py --dry-run
```

If the dry run succeeds, execute the actual loading process:

```bash
python scripts/load_all_data.py
```

The loading process follows this dependency order:

1. Airports
2. Runways
3. Gates
4. Flights
5. Gate bookings
6. Staff
7. Crew rosters

The loaders support duplicate prevention and database integrity checks.

### Step 6: Verify Database Records

```bash
python scripts/verify_database.py
```

This checks database record counts, duplicate identifiers, foreign-key integrity, missing values, gate booking overlaps, and crew scheduling conflicts.

To additionally test idempotency:

```bash
python scripts/verify_database.py --test-idempotency
```

## 8. Database Design

SQLite is used as the relational database for storing airport operational information.

The database schema defines tables for:

- Airports
- Runways
- Gates
- Flights
- Gate bookings
- Staff
- Crew rosters

The database uses primary keys, foreign keys, unique constraints, and other integrity rules to maintain relationships between records.

The database connection is managed through:

```text
database/db.py
```

The schema is maintained in:

```text
database/schema.sql
```

## 9. Automated Testing

The project uses Pytest to validate data quality, database loading, and synthetic data generation.

Run all tests:

```bash
python -m pytest tests/ -v
```

Run individual test modules:

```bash
python -m pytest tests/test_airport_data.py -v
```

```bash
python -m pytest tests/test_database_loaders.py -v
```

```bash
python -m pytest tests/test_synthetic_data.py -v
```

### Current Test Results

The current test suite contains 23 automated tests.

| Test Module | Passed |
|---|---:|
| Airport data tests | 5 |
| Database loader tests | 5 |
| Synthetic data tests | 13 |
| **Total** | **23/23** |

All 23 tests passed in the latest recorded execution.

## 10. Dependencies

The project dependencies are maintained in `requirements.txt`.

```text
pandas==3.1.0
pytest==9.2.0
```

Install all dependencies using:

```bash
python -m pip install -r requirements.txt
```

Python standard libraries such as `sqlite3`, `csv`, `pathlib`, and `argparse` do not require separate installation.

## 11. GitHub and File Management

The following files should be maintained in GitHub:

- Python source code.
- SQL database schema.
- Raw datasets.
- Processed datasets.
- Synthetic CSV datasets.
- Automated test files.
- Requirements file.
- README documentation.
- Git ignore configuration.

The following generated or environment-specific files should not be committed:

- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- `*.pyc`
- Local SQLite database files (`*.db`, `*.sqlite`).

These exclusions are configured in `.gitignore`.

## 12. Important Notes

1. Keep raw and processed datasets separate.
2. Do not manually modify generated synthetic datasets unless required.
3. Run data validation before database loading.
4. Use the dry-run option before actual database insertion.
5. Maintain database schema changes carefully.
6. Activate the virtual environment before installing dependencies or executing scripts.
7. Run automated tests after modifying data processing or database loader scripts.

## 13. Expected Outcome

After successful execution of the Data Integration pipeline:

- Raw airport and runway datasets are cleaned.
- Processed master datasets are generated.
- Synthetic operational datasets are created.
- SQLite tables are initialized.
- Master and synthetic records are loaded in dependency order.
- Referential integrity and operational constraints are validated.
- Automated tests verify the core data integration functionality.

---

**Module:** Airport Operations Coordination Engine  
**Component:** Data Integration  
**Primary Technologies:** Python, Pandas, SQLite, Pytest  
**Status:** Core data integration tests passing (23/23).
