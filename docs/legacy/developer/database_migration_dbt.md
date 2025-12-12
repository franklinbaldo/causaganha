# Developer Guide: Database Migration to dbt-duckdb

This document outlines the project's migration to `dbt-duckdb` for managing database schema, transformations, tests, and documentation. It's based on the plan detailed in `docs/plans/dtb.md`.

## 1. Rationale: Why dbt-duckdb?

The move to `dbt-duckdb` aims to simplify database management by:

- **Unifying Tools**: Using `dbt` for DDL, tests, and documentation.
- **Leveraging DuckDB's Power**: Full SQL support, direct Parquet/CSV reads, and fast embedded performance.
- **Improving Data Quality**: Built-in testing for constraints like `not_null` and `unique`.
- **Ensuring Reproducibility**: Models are rebuilt from source, promoting idempotent operations in production.
- **Future-Proofing**: Easy transition to other database backends (e.g., MotherDuck, Postgres) if needed, while keeping the same dbt models.

## 2. Developer Setup

### Installation

Add `dbt-duckdb` to your Python environment:

```bash
uv pip install "dbt-duckdb~=1.9"
```

_(Note: Ensure this is also in `pyproject.toml` dev dependencies)_

### Project Initialization (One-time by project lead)

A dbt project will be initialized (e.g., `dbt init causa_ganha --adapter duckdb`). For most developers, you will pull this project structure from the repository. The dbt project root is proposed to be `dbt/`.

### Profile Configuration

`dbt` uses a `profiles.yml` file, typically located in `~/.dbt/`. For this project, configure it as follows:

```yaml
# In ~/.dbt/profiles.yml
causa_ganha:
  target: local
  outputs:
    local:
      type: duckdb
      path: data/causaganha.duckdb # Path relative to the repository root
```

The `data/causaganha.duckdb` file is the actual DuckDB database file and should be in `.gitignore`.

After setup, run `dbt debug --project-dir dbt` (assuming `dbt/` is the project directory) to verify the connection. This will create the database file if it doesn't exist.

## 3. Repository Layout (Proposed)

```
.
├── data/                       # .duckdb database file lives here (gitignored)
├── dbt/                        # dbt project root
│   ├── models/                 # SQL definitions for tables/views
│   │   ├── staging/            # Models for 1-to-1 raw data ingestion & light cleaning
│   │   ├── marts/              # Analytical/reporting tables (e.g., rankings)
│   │   └── seeds/              # CSV reference data (e.g., court codes)
│   └── tests/                  # Custom SQL-based data tests
├── src/                        # Application code (FastAPI, CLI)
└── .github/workflows/          # CI pipeline for dbt builds
```

## 4. Core dbt Concepts

- **Models (`.sql`)**: A `SELECT` statement that defines a table or view. dbt handles the DDL (`CREATE TABLE/VIEW AS`).
  - Located in `dbt/models/`.
  - Organized into subdirectories like `staging` (raw data) and `marts` (transformed, analytical data).
  - Example: `dbt/models/staging/tjro_diary.sql`

    ```sql
    {{ config(materialized='table') }} -- Configures as a table

    CREATE OR REPLACE TABLE {{ this }} AS -- {{ this }} refers to the model itself
    SELECT
        dj.id,
        dj.date,
        dj.url_archive,
        dj.file_hash
    FROM read_parquet('raw/tjro_diary_*.parquet') dj; -- Reads directly from Parquet
    ```

- **Tests (`.yml`)**: Assertions about your data.
  - Defined in `.yml` files alongside models.
  - Generic tests: `not_null`, `unique`, `accepted_values`, `relationships`.
  - Singular tests: Custom SQL queries that should return zero rows to pass.
  - Example: `dbt/models/marts/advocate_ranking.yml`
    ```yaml
    version: 2
    models:
      - name: advocate_ranking # Corresponds to advocate_ranking.sql
        columns:
          - name: advocate
            tests:
              - not_null
              - unique
    ```
- **Seeds (`.csv`)**: CSV files in the `dbt/seeds/` directory that can be loaded into the database as tables. Useful for small, static reference data.

## 5. Local Development Workflow

All commands should be run from the repository root, specifying the project directory for dbt.

- **Build everything (models, tests, docs snapshot):**
  ```bash
  dbt build --project-dir dbt
  ```
- **Run models iteratively:**
  ```bash
  dbt run --select staging.tjro_diary --project-dir dbt  # Run a specific model
  dbt run --project-dir dbt                             # Run all models
  ```
- **Test models:**
  ```bash
  dbt test --select advocate_ranking --project-dir dbt # Test a specific model
  dbt test --project-dir dbt                            # Test all models
  ```
- **Fresh rebuild (during alpha/heavy development):**
  The database file `data/causaganha.duckdb` can be safely deleted. Then, run `dbt build --project-dir dbt` to recreate it from scratch based on the models. A helper script `causaganha db reset` might be provided.

## 6. CLI Integration

The existing `causaganha db migrate` command will be updated to call `dbt build` internally:

```python
# Conceptual change in src/cli.py or similar
import subprocess

def db_migrate_command():
    """Rebuilds dbt models to the latest state."""
    subprocess.check_call(["dbt", "build", "--project-dir", "dbt"])
```

## 7. Schema Overview & Approach

With dbt, the "schema" is defined by the collection of SQL models.

- **Staging Layer (`dbt/models/staging/`)**:
  - Tables that represent a 1-to-1 mapping or light transformation of raw source data.
  - Example: `stg_tjro_diarios` might load data directly from raw Parquet files containing TJRO diario information.
- **Marts Layer (`dbt/models/marts/`)**:
  - Tables built from staging models, often involving joins, aggregations, and business logic.
  - These are the tables typically used for analytics and application features.
  - Example: `advocate_ranking` would calculate advocate rankings based on data processed through the staging layer.

The exact table structures will be defined by the SQL in each model file. Developers should refer to these SQL files for column definitions and sources.

## 8. CI/CD (Continuous Integration)

A GitHub Actions workflow will be set up to:

1.  Install dbt and dependencies.
2.  Run `dbt build --project-dir dbt` to build models and run tests.
3.  Perform a **drift check**: Ensure that all models defined in the project are actually built and materialized in the database. If there's a discrepancy (e.g., a model SQL file exists but `dbt build` didn't create it, or an old table exists that's no longer a model), the CI build will fail.

## 9. Future dbt Features (Optional but Powerful)

- **Seeds**: Load static CSV data (e.g., court codes) using `dbt seed --project-dir dbt`.
- **Snapshots**: Track changes to mutable data over time (e.g., advocate status changes) using `dbt snapshot --project-dir dbt`.
- **Documentation**: Auto-generate a data lineage and documentation website using `dbt docs generate --project-dir dbt && dbt docs serve --project-dir dbt`.

This migration aims to streamline database development and improve data quality. Refer to the official [dbt documentation](https://docs.getdbt.com/) for more in-depth information.

```

```
