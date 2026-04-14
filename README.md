# CausaGanha

![Collect ZIPs](https://github.com/franklinbaldo/causaganha/actions/workflows/collect-zips.yml/badge.svg)
![Deploy Web](https://github.com/franklinbaldo/causaganha/actions/workflows/deploy-web.yml/badge.svg)
![Status](https://img.shields.io/badge/status-alpha-orange?style=for-the-badge)

CausaGanha is a judicial data platform focused on the Brazilian DJEN ecosystem. The project collects judicial communications, archives raw ZIPs on Internet Archive, consolidates them into analytics-friendly Parquet datasets, and serves a public dashboard with coverage and publication views.

Live dashboard: [https://franklinbaldo.github.io/causaganha/](https://franklinbaldo.github.io/causaganha/)

## What the project does

- Collects DJEN ZIPs continuously and archives them on Internet Archive.
- Consolidates daily raw data into structured Parquet tables.
- Maintains a catalog and dashboard cache for public browsing.
- Includes Python workflows for collection, analysis, scoring, archival, and backfill.
- Ships an Astro + Svelte frontend for public exploration.

## Current architecture

The repository has two main runtime surfaces:

- Python backend and CLI in [src/causaganha](src/causaganha) and [src/djen_backup](src/djen_backup)
- Web frontend in [web](web)

High-level flow:

1. **djen-backup** — manifest-driven sync engine. Tracks every `(tribunal, date)` pair in a single CSV (`sync-manifest.csv`) stored on Internet Archive. Workers check DJEN availability, download ZIPs, upload to IA, and record raw response codes (404, 400, 403, timeout, etc.) for accurate status tracking.
2. **Consolidate Parquet** — converts complete daily ZIP batches into Parquet tables.
3. **Update Catalog** — refreshes metadata used by downstream consumers.
4. **Deploy Web** — renders query contracts (`.qmd` files in `web/src/queries/`) to JSON and publishes the Astro site to GitHub Pages.

### Sync manifest

The source of truth for what's been archived is `sync-manifest.csv` at `https://archive.org/download/causaganha-dashboard/sync-manifest.csv`. Each row:

```csv
tribunal,date,ia_status,djen_status,djen_raw,updated_at
TJSP,2025-01-15,uploaded,,200,2026-04-14T10:00:00
TJSP,2025-01-16,,absent,404,2026-04-14T10:01:00
```

The engine periodically (every 10 min) uploads the manifest and a compact `manifest-summary.json` to IA, so progress is never lost to crashes.

The main GitHub Actions workflows in [.github/workflows](/Users/frank/workspace/causaganha/.github/workflows) are:

- [collect-zips.yml](/Users/frank/workspace/causaganha/.github/workflows/collect-zips.yml)
- [collect-today.yml](/Users/frank/workspace/causaganha/.github/workflows/collect-today.yml)
- [consolidate-parquet.yml](/Users/frank/workspace/causaganha/.github/workflows/consolidate-parquet.yml)
- [update-catalog.yml](/Users/frank/workspace/causaganha/.github/workflows/update-catalog.yml)
- [deploy-web.yml](/Users/frank/workspace/causaganha/.github/workflows/deploy-web.yml)
- [test.yml](/Users/frank/workspace/causaganha/.github/workflows/test.yml)

## Key constraints

- Internet Archive uploads must use `httpx`-based logic. Do not migrate IA uploads to `boto3`.
- Local runs in Brazil should use direct DJEN access by default. Use the Cloud Run proxy only when `--use-proxy` or `DJEN_USE_PROXY=1` is explicitly set, such as in GitHub Actions.
- The repository is mid-refactor. Some legacy scripts and older docs still exist, but the source of truth is the current code and workflows in this repo.

## Quick start

```bash
uv sync --dev
cp .env.example .env
uv run pre-commit install
uv run pytest -q
```

## Python CLIs

Two CLI entrypoints:

### `djen-backup` — sync engine

```bash
# Full sync (check DJEN + download + upload to IA)
uv run djen-backup --workers 8

# Only verify DJEN availability, no downloads
uv run djen-backup check --workers 8

# Only download+upload entries already marked available
uv run djen-backup upload --workers 4
```

Subcommand modes:

| Mode    | Checkers | Downloaders | Uploaders |
|---------|----------|-------------|-----------|
| default | ✓        | ✓           | ✓         |
| check   | ✓        | ✗           | ✗         |
| upload  | ✗        | ✓           | ✓         |

All modes persist the manifest to IA every 10 minutes. See `uv run djen-backup --help`.

### `causaganha` — data pipeline CLI

Available top-level commands include: `collect`, `analyze`, `score`, `db`, `export-parquet`, `backfill`, `archival`, `groundtruth`, `parquet`, `catalog`.

```bash
uv run causaganha --help
```

## Web frontend

The frontend lives in [web](web) and uses:

- Astro 5
- Svelte 5
- DuckDB WASM
- Vitest
- ESLint
- Zod

### Query contracts

The frontend declares its data needs via Quarto-compatible `.qmd` files in [web/src/queries/](web/src/queries/). Each file has YAML frontmatter (output path + format) plus a SQL code block that runs against the manifest. The backend executes these during deploy and publishes JSON to `web/public/data/`.

To add a new view:

1. Create `web/src/queries/my_view.qmd` with frontmatter and a SQL block
2. Add a typed loader in [web/src/lib/queryData.ts](web/src/lib/queryData.ts)
3. `uv run python scripts/render_queries.py` generates the JSON

See [web/src/queries/README.md](web/src/queries/README.md) for the full contract.

Useful commands:

```bash
cd web
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
web/                     Astro + Svelte frontend
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
cd web && npm ci && npm run lint && npm test && npm run build
```

## Environment

Start from [.env.example](/Users/frank/workspace/causaganha/.env.example). Common variables include:

- `GEMINI_API_KEY`
- `IA_ACCESS_KEY` / `IA_SECRET_KEY`
- `IAS3_ACCESS_KEY` / `IAS3_SECRET_KEY`
- `DJEN_DIRECT_URL`
- `DJEN_PROXY_URL`
- `DJEN_USE_PROXY`
- `ENABLED_TRIBUNALS`
- `LOG_LEVEL`

## Testing and CI

The main CI workflow is [test.yml](/Users/frank/workspace/causaganha/.github/workflows/test.yml). It currently runs:

1. Python formatting and lint checks
2. Dead code check with `vulture`
3. Python tests
4. Frontend lint, test, and build

## Documentation status

This repository had stale documentation. The files in the project root are now the main source of truth:

- [README.md](/Users/frank/workspace/causaganha/README.md)
- [CONTRIBUTING.md](/Users/frank/workspace/causaganha/CONTRIBUTING.md)
- [src/causaganha/README.md](/Users/frank/workspace/causaganha/src/causaganha/README.md)

If a doc disagrees with code or workflow files, trust the code and update the doc in the same change.

## License

MIT
