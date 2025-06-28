#!/usr/bin/env bash
# Install pre-commit hooks for the repository
set -euo pipefail

if ! command -v pre-commit >/dev/null 2>&1; then
  echo "pre-commit is not installed. Run 'uv sync --dev' first." >&2
  exit 1
fi

pre-commit install --install-hooks
