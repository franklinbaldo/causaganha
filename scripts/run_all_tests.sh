#!/bin/bash
set -e

echo "--- Running Pytest tests ---"
pytest

echo "\n--- Running dbt tests ---"
# Ensure dbt project path is correct if not running from dbt project root
# Assuming dbt project is in /app/dbt/ as per dtb.md plan for repo layout
if [ -d "/app/dbt" ]; then
  # Check if dbt profiles.yml is correctly set up for non-interactive use in CI/test runner
  # This might require DBT_PROFILES_DIR to be set or profiles.yml to be in /app/dbt
  # For local docker-compose runs, if ~/.dbt/profiles.yml is not mounted, this might need adjustment.
  # However, the dtb.md plan suggests a profiles.yml that uses a path relative to repo root,
  # which should work fine with current volume mounts if dbt is run from /app.
  echo "Attempting to run dbt tests with project directory /app/dbt..."
  dbt test --project-dir /app/dbt
else
  echo "INFO: dbt project directory not found at /app/dbt. Skipping dbt tests."
  echo "If this is unexpected, ensure the dbt project is initialized at './dbt/' in the repo root."
fi

echo "\n--- All tests complete ---"
