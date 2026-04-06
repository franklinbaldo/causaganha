# CLAUDE.md — CausaGanha Development Guide

## What is this project?

CausaGanha is a judicial analytics platform that scrapes legal gazettes (DJEN) from 91 Brazilian courts, archives them on Internet Archive, and serves a public analytics dashboard with lawyer performance ratings using the OpenSkill algorithm.

- **Status:** Alpha (V2 refactoring in progress)
- **License:** MIT
- **Dashboard:** https://franklinbaldo.github.io/causaganha/

## Quick Start

```bash
uv sync --dev                    # Install all dependencies
cp .env.example .env             # Configure environment (edit .env)
uv run pre-commit install        # Install git hooks
uv run pytest -q                 # Run tests
```

Or use the Makefile:
```bash
make setup     # Full dev environment setup
make test      # Run Python tests
make lint      # Run ruff format check + lint
make fix       # Auto-fix lint issues and format code
make check     # Run all CI checks locally (lint + test + dashboard)
```

## Project Layout

```
src/causaganha/          # Main Python package
  cli/                   # Typer CLI commands
  pipeline/              # Data pipeline (collect, analyze, score)
  analysis/              # AI analysis (LLM, RAG, embeddings)
  storage/               # DuckDB + Parquet storage
  scoring/               # OpenSkill rating algorithm
  catalog/               # DuckDB catalog generator
  clients/               # External service clients
  config.py              # Pydantic configuration
src/djen_backup/         # Backup/collection utilities
dashboard/               # Astro + Preact UI (separate npm project)
tests/                   # BDD (pytest-bdd) and unit tests
scripts/                 # Pipeline, dashboard, and dev scripts
```

## Key Commands

| Task | Command |
|------|---------|
| Run all tests | `uv run pytest -q` |
| Run specific test | `uv run pytest -k test_name` |
| Format code | `uv run ruff format` |
| Lint code | `uv run ruff check` |
| Auto-fix lint | `uv run ruff check --fix` |
| Dead code check | `uvx vulture src/ scripts/ vulture_whitelist.py --min-confidence 100` |
| CLI help | `uv run causaganha --help` |
| Dashboard dev | `cd dashboard && npm install && npm run dev` |
| Dashboard test | `cd dashboard && npm test` |
| Dashboard build | `cd dashboard && npm run build` |

## Architecture Decisions

- **Internet Archive uploads MUST use `httpx`** — never `boto3`. IA's S3-compatible API has metadata header requirements (`x-archive-meta-*`) that `boto3` cannot satisfy. Two migration attempts both broke the pipeline (see PR #348).
- **DJEN API is geo-blocked** to Brazilian IPs. A reverse proxy on Google Cloud Run (São Paulo) is used: `https://djen-proxy-mhgmawcn3a-rj.a.run.app`
- **Data identity:** Lawyer identity uses OAB + UF only (not name) to prevent variant duplicates.
- **UUIDv5** deterministic identifiers for deduplication across the data lake.
- **DuckDB + Ibis** for analytics queries (migrating away from raw SQL).
- **Parquet** as the consolidated storage format (daily files, not per-tribunal).

## Code Style

- **Linter/Formatter:** `ruff` (config in `ruff.toml`) — ALL rules enabled with selective ignores
- **Line length:** 100 characters
- **Target:** Python 3.12+
- **Quotes:** Double quotes
- **Docstrings:** Google convention
- **Type hints:** Strongly encouraged
- **Pre-commit hooks:** ruff lint+format, trailing whitespace, YAML/TOML/JSON checks

## Testing

- Framework: `pytest` + `pytest-bdd` for behavior-driven tests
- Async: `pytest-asyncio` (auto mode)
- HTTP mocking: `respx`
- Tests live in `tests/` with BDD `.feature` files alongside step definitions
- CI runs tests with tribunal matrix (`tjro`)

## CI Pipeline

GitHub Actions (`.github/workflows/test.yml`) runs on every PR and push to main:
1. **Lint:** `ruff format --check` + `ruff check` + `vulture` dead code check
2. **Tests:** `pytest` with tribunal matrix
3. **Dashboard:** `npm ci` → lint → test → build

## Environment Variables

Copy `.env.example` to `.env`. Key variables:
- `GEMINI_API_KEY` — required for PDF extraction
- `IA_ACCESS_KEY` / `IA_SECRET_KEY` — required for Internet Archive uploads
- `JINA_API_KEY` — optional, for Jina embeddings
- `LOG_LEVEL` — DEBUG/INFO/WARNING/ERROR
- `ENABLED_TRIBUNALS` — comma-separated tribunal codes (default: `tjro`)

## Common Patterns

### Adding a new CLI command
Add to `src/causaganha/cli/` following existing Typer command patterns.

### Adding a new tribunal
1. Find the gazette URL (`diariooficial.tjXX.jus.br`)
2. Follow patterns in `src/causaganha/pipeline/collect.py`
3. Add tribunal code to `TRIBUNAIS` in `src/causaganha/config.py`
4. Write tests (required)

### Running the local pipeline
```bash
make pipeline-small   # Collect 5 items → consolidate → embed → catalog → dashboard
```
Requires `IAS3_ACCESS_KEY` and `IAS3_SECRET_KEY` in environment.
