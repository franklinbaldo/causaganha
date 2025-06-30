#!/bin/bash
set -e

# This script resets the dbt-managed DuckDB database and rebuilds it.
# It assumes the dbt project is located in a 'dbt/' directory at the repository root,
# and the DuckDB file is at 'data/causaganha.duckdb'.

DB_FILE="data/causaganha.duckdb"
DBT_PROJECT_DIR="dbt" # Relative to repository root

echo "--- Resetting dbt Database ---"

if [ -f "$DB_FILE" ]; then
  echo "Removing existing database file: $DB_FILE"
  rm -f "$DB_FILE"
else
  echo "Database file $DB_FILE not found. Skipping removal."
fi

echo "\nRunning dbt build to reconstruct the database..."
if [ -d "$DBT_PROJECT_DIR" ]; then
  # Ensure dbt can find profiles.yml. Typically uses ~/.dbt/profiles.yml
  # or DBT_PROFILES_DIR environment variable.
  # The profiles.yml specified in dtb.md uses a path relative to repo root for the db file,
  # so running dbt from repo root with --project-dir should work.
  dbt build --project-dir "$DBT_PROJECT_DIR"

  # Optionally, run tests after build
  # echo "\nRunning dbt tests..."
  # dbt test --project-dir "$DBT_PROJECT_DIR"
else
  echo "ERROR: dbt project directory '$DBT_PROJECT_DIR' not found."
  echo "Cannot rebuild database. Please ensure dbt project is initialized."
  exit 1
fi

echo "\n✅ Fresh database built successfully using dbt."
