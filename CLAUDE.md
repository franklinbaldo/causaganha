# CLAUDE.md

![Alpha](https://img.shields.io/badge/status-alpha-orange?style=for-the-badge)

> Development guidance for CausaGanha repository.

## Project Overview

**Mission:** Eliminate information asymmetry in the Brazilian legal market through transparent, data-driven lawyer performance ratings.

CausaGanha collects judicial communication data from the **DJEN API**, archives it on **Internet Archive**, and scores lawyer performance using the **OpenSkill** algorithm.

### Key Insight: Structured Data

DJEN provides **structured data** directly (lawyer names, OAB numbers, parties, case numbers). We don't need expensive LLM parsing - the API already gives us structured information about who is involved in each case.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      DATA PIPELINE                              │
└─────────────────────────────────────────────────────────────────┘

DJEN API (geo-blocked) → DJEN Proxy (Cloud Run, São Paulo)
                              │
                              ▼
                    GitHub Actions (5 min)
                    Download ZIP → Upload IA
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   INTERNET ARCHIVE                              │
│                                                                 │
│  djen-YYYY-MM-DD/                    ← One item per day         │
│  ├── djen-YYYY-MM-DD-TJSP.zip                                  │
│  ├── djen-YYYY-MM-DD-TJSP-comunicacoes.parquet                 │
│  ├── djen-YYYY-MM-DD-TJSP-advogados.parquet                    │
│  ├── djen-YYYY-MM-DD-TJSP-partes.parquet                       │
│  ├── djen-YYYY-MM-DD-TJRO.zip                                  │
│  └── ... (all 91 courts)                                       │
│                                                                 │
│  causaganha-catalog/                 ← Master catalog           │
│  ├── catalog.duckdb                                            │
│  ├── catalog.sql                                               │
│  └── manifest.parquet                                          │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
src/causaganha/
├── cli/                 # Typer CLI (single entry point)
├── pipeline/            # Data orchestration
│   ├── collect.py       # Download from DJEN
│   ├── analyze.py       # Decision classification
│   ├── score.py         # OpenSkill ratings
│   ├── parquet_export.py
│   ├── ia_upload.py     # Internet Archive upload
│   └── ia_download.py   # Internet Archive download
├── analysis/            # AI analysis
│   ├── analyzer.py      # LLM analyzer (Pydantic AI)
│   ├── rag_analyzer.py  # Embedding-based analyzer
│   ├── hybrid_analyzer.py
│   ├── embedding_service.py
│   └── models.py        # DecisionAnalysis Pydantic model
├── storage/             # Data layer
│   ├── connection.py    # DuckDB singleton (Ibis)
│   ├── queries.py       # Data access
│   ├── schema.sql       # Table definitions
│   └── migrations.py    # Schema migrations
├── scoring/             # Rating system
│   └── openskill.py     # Plackett-Luce algorithm
├── catalog/             # DuckDB catalog generator
│   └── creator.py       # Creates catalogs with remote views
├── clients/             # External services
│   └── archive.py       # Internet Archive client
└── config.py            # Pydantic Settings

djen-scraper/            # Scraping infrastructure (separate)
├── dashboard/           # Status dashboard (React)
└── scripts/             # convert_to_parquet.py

.github/workflows/       # Automated pipelines
├── archive-zips.yml     # Collection (every 5 min)
├── convert-parquet.yml  # Conversion (every 10 min)
├── update-catalog.yml   # Catalog generation (daily)
├── daily-embeddings.yml # Embedding generation
└── test.yml             # CI/CD

scripts/
└── generate_catalog.py  # Catalog generation script
```

## Development Setup

```bash
uv venv
source .venv/bin/activate
uv sync --dev
```

## Core Commands

```bash
# CLI help
causaganha --help

# Database
causaganha db init
causaganha db status
causaganha db migrate

# Download from Internet Archive
causaganha parquet download TJRO 2026-01-15
causaganha parquet analyze TJRO 2026-01-15

# Ground truth (for RAG)
causaganha groundtruth init
causaganha groundtruth sync
causaganha groundtruth search "query"

# Catalog management (Internet Archive)
causaganha catalog download                    # Download catalog from IA
causaganha catalog backfill-status             # Show what data is missing
causaganha catalog query "SELECT * FROM manifest LIMIT 10"

# Catalog management (Local)
causaganha catalog create --output catalog.duckdb
causaganha catalog validate catalog.duckdb
```

## Testing

```bash
# Run all tests
uv run pytest

# Run BDD features
uv run pytest tests/features/

# Run with coverage
uv run pytest --cov=causaganha
```

## Internet Archive Structure

```
djen-YYYY-MM-DD/                       ← Item per day
├── djen-YYYY-MM-DD-TRIBUNAL.zip       ← Raw JSON (source)
├── djen-YYYY-MM-DD-TRIBUNAL-comunicacoes.parquet
├── djen-YYYY-MM-DD-TRIBUNAL-advogados.parquet
├── djen-YYYY-MM-DD-TRIBUNAL-partes.parquet
├── djen-YYYY-MM-DD-TRIBUNAL-comunicacao_partes.parquet
└── djen-YYYY-MM-DD-TRIBUNAL-comunicacao_advogados.parquet

causaganha-catalog/                    ← Master catalog
├── catalog.duckdb                     ← DuckDB with remote views
├── catalog.sql                        ← SQL definition (portable)
├── manifest.parquet                   ← Index of all files on IA
└── backfill-needed.parquet            ← What data needs to be collected
```

## DJEN Proxy

The DJEN API is geo-blocked to Brazilian IPs. We use a proxy on Google Cloud Run:

- **URL**: `https://djen-proxy-mhgmawcn3a-rj.a.run.app`
- **Source**: `djen_proxy.go`
- **Docs**: `docs/DJEN_PROXY.md`

## Key Documentation

- `README.md` - Project overview
- `docs/CATALOG.md` - Catalog system and backfill tracking
- `docs/DJEN_API.md` - DJEN API endpoints and data structures
- `docs/DJEN_PROXY.md` - Proxy documentation
- `DJEN_INFRASTRUCTURE.md` - Full infrastructure details

## Code Quality

- **Linting**: Ruff (strict)
- **Type checking**: MyPy (strict mode)
- **Pre-commit**: Enforced via hooks

```bash
# Format and lint
uv run ruff format
uv run ruff check --fix

# Type check
uv run mypy src/
```
