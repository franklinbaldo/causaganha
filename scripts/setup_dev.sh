#!/usr/bin/env bash
set -e

uv venv
source .venv/bin/activate
uv sync --dev
uv pip install -e .
pre-commit install --install-hooks
