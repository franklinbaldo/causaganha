# CausaGanha

![Collect ZIPs](https://github.com/franklinbaldo/causaganha/actions/workflows/collect-zips.yml/badge.svg)
![Deploy Dashboard](https://github.com/franklinbaldo/causaganha/actions/workflows/deploy-dashboard.yml/badge.svg)
![Status](https://img.shields.io/badge/status-alpha-orange?style=for-the-badge)

CausaGanha is a judicial data platform focused on the Brazilian DJEN ecosystem. The project collects judicial communications, archives raw ZIPs on Internet Archive, consolidates them into analytics-friendly Parquet datasets, and serves a public dashboard with coverage and publication views.

Live dashboard: [https://franklinbaldo.github.io/causaganha/](https://franklinbaldo.github.io/causaganha/)

## What the project does

- Collects DJEN ZIPs continuously and archives them on Internet Archive.
- Consolidates daily raw data into structured Parquet tables.
- Maintains a catalog and dashboard cache for public browsing.
- Includes Python workflows for collection, analysis, scoring, archival, and backfill.
- Ships an Astro + Svelte dashboard for public exploration.

## Current architecture

The repository currently has two main runtime surfaces:

- Python backend and CLI in [src/causaganha](/Users/frank/workspace/causaganha/src/causaganha)
- Dashboard frontend in [dashboard](/Users/frank/workspace/causaganha/dashboard)

High-level flow:

1. `Collect ZIPs` downloads DJEN ZIPs and uploads them to Internet Archive.
2. `Consolidate Parquet` converts complete daily ZIP batches into Parquet tables.
3. `Update Catalog` refreshes metadata used by downstream consumers.
4. `Deploy Dashboard` publishes the Astro site to GitHub Pages.

The main GitHub Actions workflows in [.github/workflows](/Users/frank/workspace/causaganha/.github/workflows) are:

- [collect-zips.yml](/Users/frank/workspace/causaganha/.github/workflows/collect-zips.yml)
- [collect-today.yml](/Users/frank/workspace/causaganha/.github/workflows/collect-today.yml)
- [consolidate-parquet.yml](/Users/frank/workspace/causaganha/.github/workflows/consolidate-parquet.yml)
- [update-catalog.yml](/Users/frank/workspace/causaganha/.github/workflows/update-catalog.yml)
- [deploy-dashboard.yml](/Users/frank/workspace/causaganha/.github/workflows/deploy-dashboard.yml)
- [test.yml](/Users/frank/workspace/causaganha/.github/workflows/test.yml)

## Key constraints

- Internet Archive uploads must use `httpx`-based logic. Do not migrate IA uploads to `boto3`.
- DJEN access is geo-restricted, so the project supports a Cloud Run proxy through `DJEN_PROXY_URL`.
- The repository is mid-refactor. Some legacy scripts and older docs still exist, but the source of truth is the current code and workflows in this repo.

## Quick start

```bash
uv sync --dev
cp .env.example .env
uv run pre-commit install
uv run pytest -q
```

## Python CLI

The installed CLI entrypoint is `causaganha`.

Available top-level commands currently include:

- `collect`
- `analyze`
- `score`
- `db`
- `export-parquet`
- `export-status`
- `backfill`
- `archival`
- `groundtruth`
- `parquet`
- `catalog`

Inspect the current CLI surface with:

```bash
uv run causaganha --help
```

## Dashboard

The dashboard lives in [dashboard](/Users/frank/workspace/causaganha/dashboard) and uses:

- Astro 5
- Svelte 5
- DuckDB WASM
- Vitest
- ESLint
- Zod

Useful commands:

```bash
cd dashboard
npm ci
npm run dev
npm run lint
npm test
npm run build
```

If you already use Bun locally, `bun install` and `bun run build` also work for development, but CI is currently based on `npm`.

## Repository structure

```text
src/causaganha/          Python package
src/djen_backup/         ZIP/backfill collection utilities
dashboard/               Astro + Svelte frontend
scripts/                 Operational and pipeline scripts
tests/                   Pytest and pytest-bdd suites
.github/workflows/       CI/CD and data workflows
```

Important Python package areas:

- [src/causaganha/analysis](/Users/frank/workspace/causaganha/src/causaganha/analysis)
- [src/causaganha/archival](/Users/frank/workspace/causaganha/src/causaganha/archival)
- [src/causaganha/catalog](/Users/frank/workspace/causaganha/src/causaganha/catalog)
- [src/causaganha/clients](/Users/frank/workspace/causaganha/src/causaganha/clients)
- [src/causaganha/compliance](/Users/frank/workspace/causaganha/src/causaganha/compliance)
- [src/causaganha/pipeline](/Users/frank/workspace/causaganha/src/causaganha/pipeline)
- [src/causaganha/scoring](/Users/frank/workspace/causaganha/src/causaganha/scoring)
- [src/causaganha/storage](/Users/frank/workspace/causaganha/src/causaganha/storage)

## Development commands

Common local commands:

```bash
uv run pytest -q
uv run ruff format --check
uv run ruff check
uvx vulture src/ scripts/ vulture_whitelist.py --min-confidence 100
cd dashboard && npm ci && npm run lint && npm test && npm run build
```

## Environment

Start from [.env.example](/Users/frank/workspace/causaganha/.env.example). Common variables include:

- `GEMINI_API_KEY`
- `IA_ACCESS_KEY` / `IA_SECRET_KEY`
- `IAS3_ACCESS_KEY` / `IAS3_SECRET_KEY`
- `DJEN_PROXY_URL`
- `ENABLED_TRIBUNALS`
- `LOG_LEVEL`

## Testing and CI

The main CI workflow is [test.yml](/Users/frank/workspace/causaganha/.github/workflows/test.yml). It currently runs:

1. Python formatting and lint checks
2. Dead code check with `vulture`
3. Python tests
4. Dashboard lint, test, and build

## Documentation status

This repository had stale documentation. The files in the project root are now the main source of truth:

- [README.md](/Users/frank/workspace/causaganha/README.md)
- [CONTRIBUTING.md](/Users/frank/workspace/causaganha/CONTRIBUTING.md)
- [src/causaganha/README.md](/Users/frank/workspace/causaganha/src/causaganha/README.md)

If a doc disagrees with code or workflow files, trust the code and update the doc in the same change.

## License

MIT
