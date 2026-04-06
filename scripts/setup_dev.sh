#!/usr/bin/env bash
# CausaGanha — Developer Environment Setup
# Usage: bash scripts/setup_dev.sh
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[x]${NC} $1"; }

echo "=== CausaGanha Developer Setup ==="
echo ""

# --- Check prerequisites ---------------------------------------------------
missing=0

if ! command -v uv &>/dev/null; then
    error "uv not found. Install it: https://docs.astral.sh/uv/getting-started/installation/"
    missing=1
fi

if ! command -v python3 &>/dev/null; then
    error "python3 not found."
    missing=1
else
    py_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)" 2>/dev/null; then
        info "Python $py_version detected"
    else
        error "Python 3.12+ required (found $py_version)"
        missing=1
    fi
fi

if ! command -v node &>/dev/null; then
    warn "node not found — dashboard dev will not work. Install Node.js 22+ for dashboard development."
else
    info "Node $(node --version) detected"
fi

if ! command -v git &>/dev/null; then
    error "git not found."
    missing=1
fi

if [ "$missing" -ne 0 ]; then
    echo ""
    error "Fix the above issues and re-run this script."
    exit 1
fi

# --- Python dependencies ---------------------------------------------------
info "Installing Python dependencies..."
uv sync --dev

# --- Pre-commit hooks ------------------------------------------------------
info "Installing pre-commit hooks..."
uv run pre-commit install --install-hooks

# --- Environment file -------------------------------------------------------
if [ ! -f .env ]; then
    cp .env.example .env
    info "Created .env from .env.example"
    warn "Edit .env with your API keys before running the pipeline."
else
    info ".env already exists, skipping."
fi

# --- Dashboard (optional) ---------------------------------------------------
if command -v node &>/dev/null && [ -d dashboard ]; then
    info "Installing dashboard dependencies..."
    (cd dashboard && npm install)
fi

# --- Verify -----------------------------------------------------------------
echo ""
info "Running quick verification..."
uv run ruff --version
uv run pytest --co -q 2>/dev/null | tail -1

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Useful commands:"
echo "  make test        Run Python tests"
echo "  make lint        Check formatting and lint"
echo "  make fix         Auto-fix lint issues"
echo "  make check       Run all CI checks locally"
echo "  make dashboard   Start dashboard dev server"
echo "  make help        Show all available commands"
echo ""
