# ============================================================================
# CausaGanha — Developer Commands
# ============================================================================
# Usage:  make <target>
#
# Run `make` or `make help` to see all available targets.
# ============================================================================

.PHONY: help setup test lint fix format check dead-code audit dashboard \
        dashboard-test dashboard-build pipeline-small pipeline-large clean

.DEFAULT_GOAL := help

# --------------------------------------------------------------------------
# Help
# --------------------------------------------------------------------------
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------
setup: ## Set up dev environment (install deps, hooks, .env)
	@echo "Installing Python dependencies..."
	uv sync --dev
	@echo "Installing pre-commit hooks..."
	uv run pre-commit install --install-hooks
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example — edit it with your keys"; \
	else \
		echo ".env already exists, skipping"; \
	fi
	@echo ""
	@echo "Done! Run 'make check' to verify everything works."

# --------------------------------------------------------------------------
# Quality
# --------------------------------------------------------------------------
test: ## Run Python tests
	uv run pytest -q

test-cov: ## Run Python tests with coverage report
	uv run pytest --cov=src --cov-report=term-missing -q

lint: ## Check formatting and lint (no changes)
	uv run ruff format --check
	uv run ruff check

fix: ## Auto-fix lint issues and format code
	uv run ruff check --fix
	uv run ruff format

format: fix ## Alias for 'fix'

dead-code: ## Check for dead code with vulture
	uvx vulture src/ scripts/ vulture_whitelist.py --min-confidence 100

audit: ## Security audit of dependencies
	uv run pip-audit

check: lint test dead-code dashboard-build ## Run all CI checks locally
	@echo ""
	@echo "All checks passed!"

# --------------------------------------------------------------------------
# Dashboard (Astro/Preact)
# --------------------------------------------------------------------------
dashboard: ## Start dashboard dev server
	cd dashboard && npm install && npm run dev

dashboard-test: ## Run dashboard tests
	cd dashboard && npm test

dashboard-build: ## Build dashboard for production
	cd dashboard && npm ci && npm run lint && npm test && npm run build

# --------------------------------------------------------------------------
# Pipeline (requires IA credentials in env)
# --------------------------------------------------------------------------
pipeline-small: ## Run full pipeline with small data (5 items)
	@$(MAKE) -f Makefile.local full

pipeline-large: ## Run full pipeline with larger data (20 items)
	@$(MAKE) -f Makefile.local full-large

pipeline-collect: ## Collect only (5 items)
	@$(MAKE) -f Makefile.local collect

pipeline-consolidate: ## Consolidate ZIPs to Parquet
	@$(MAKE) -f Makefile.local consolidate

# --------------------------------------------------------------------------
# Utilities
# --------------------------------------------------------------------------
clean: ## Remove build artifacts and pipeline output
	rm -rf pipeline-output/ dist/ build/ *.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned."

pre-commit: ## Run pre-commit on all files
	uv run pre-commit run --all-files
