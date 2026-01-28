# CausaGanha

![Alpha](https://img.shields.io/badge/status-alpha-orange?style=for-the-badge)

**CausaGanha** is a judicial analytics platform that collects, archives, and analyzes data from the Brazilian DJEN (Diário de Justiça Eletrônico Nacional) to provide transparent lawyer performance ratings.

## [Live Dashboard](https://franklinbaldo.github.io/causaganha/)

## Vision

Eliminate information asymmetry in the Brazilian legal market through transparent, data-driven lawyer performance ratings based on real judicial outcomes.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CAUSAGANHA PIPELINE                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────────┐
│   DJEN API   │────▶│  DJEN Proxy  │────▶│      GitHub Actions (5min)       │
│ (geo-blocked)│     │ (Cloud Run)  │     │  Download ZIP → Upload to IA     │
└──────────────┘     └──────────────┘     └──────────────────────────────────┘
                                                         │
                                                         ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         INTERNET ARCHIVE (Data Lake)                         │
│                                                                              │
│  djen-2026-01-01/                    djen-2026-01-02/                        │
│  ├── djen-2026-01-01-TJSP.zip        ├── djen-2026-01-02-TJSP.zip           │
│  ├── djen-2026-01-01-TJSP-*.parquet  ├── djen-2026-01-02-TJSP-*.parquet     │
│  ├── djen-2026-01-01-TJRO.zip        └── ...                                │
│  └── ...                                                                     │
│                                                                              │
│  causaganha-catalog/                                                         │
│  ├── catalog.duckdb        ← Master catalog with remote views               │
│  ├── catalog.sql           ← SQL definition (portable)                      │
│  └── manifest.parquet      ← Index of all available files                   │
└──────────────────────────────────────────────────────────────────────────────┘
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              ▼                           ▼                           ▼
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│  Convert to Parquet  │   │  Generate Embeddings │   │   Analyze & Score    │
│   (GitHub Actions)   │   │   (GitHub Actions)   │   │    (OpenSkill)       │
└──────────────────────┘   └──────────────────────┘   └──────────────────────┘
```

## Data Pipeline

### 1. Collection (Every 5 minutes)

GitHub Actions downloads judicial communications from DJEN for all 91 Brazilian courts and uploads raw ZIPs to Internet Archive.

```bash
# Trigger: .github/workflows/archive-zips.yml
# Structure: djen-YYYY-MM-DD/djen-YYYY-MM-DD-TRIBUNAL.zip
```

### 2. Conversion (Every 10 minutes)

Converts ZIPs to optimized Parquet files (ZSTD compressed) and uploads to the same IA item.

```bash
# Trigger: .github/workflows/convert-parquet.yml
# Output: djen-YYYY-MM-DD-TRIBUNAL-{comunicacoes,partes,advogados,...}.parquet
```

### 3. Analysis (Daily)

- Generates embeddings for semantic search
- Classifies case outcomes (win/loss/partial)
- Calculates lawyer ratings using OpenSkill algorithm

### 4. Catalog Update (Weekly)

Updates the master DuckDB catalog with views pointing to all remote Parquet files, enabling direct queries without downloading data.

## DJEN API

The DJEN (Diário de Justiça Eletrônico Nacional) provides structured judicial communication data:

- **Lawyers**: OAB numbers, names
- **Parties**: Process parties (plaintiff, defendant)
- **Communications**: Intimations, citations, notifications
- **Processes**: Case numbers, courts, dates

**API Documentation**: See [docs/DJEN_API.md](docs/DJEN_API.md)

### Geo-blocking

The DJEN API is geo-blocked to Brazilian IPs. We use a reverse proxy on Google Cloud Run (São Paulo region) to bypass this restriction.

**Proxy URL**: `https://djen-proxy-mhgmawcn3a-rj.a.run.app`

See [docs/DJEN_PROXY.md](docs/DJEN_PROXY.md) for details.

## Quick Start

```bash
# Install dependencies
uv sync

# Initialize local database
causaganha db init

# Check database status
causaganha db status

# Download and analyze from Internet Archive
causaganha parquet download TJRO 2026-01-15
causaganha parquet analyze TJRO 2026-01-15
```

## Project Structure

```
causaganha/
├── src/causaganha/          # Main Python package
│   ├── cli/                 # Typer CLI commands
│   ├── pipeline/            # Data pipeline (collect, analyze, score)
│   ├── analysis/            # AI analysis (LLM, RAG, embeddings)
│   ├── storage/             # DuckDB + Parquet storage
│   ├── scoring/             # OpenSkill rating algorithm
│   ├── catalog/             # DuckDB catalog generator
│   └── clients/             # External service clients
├── djen-scraper/            # DJEN scraping infrastructure
│   ├── cloudflare/          # Cloudflare Worker (TypeScript)
│   ├── dashboard/           # Status dashboard (React)
│   └── scripts/             # Conversion scripts
├── .github/workflows/       # GitHub Actions pipelines
├── docs/                    # Documentation
└── tests/                   # BDD and unit tests
```

## Internet Archive Structure

All data is publicly archived on Internet Archive:

| Item Pattern | Contents |
|--------------|----------|
| `djen-YYYY-MM-DD` | Raw ZIPs + Parquet files for one day |
| `causaganha-catalog` | Master DuckDB catalog + manifest |
| `causaganha-embeddings-*` | Embedding vectors for semantic search |

## Development

```bash
# Setup
uv venv && source .venv/bin/activate
uv sync --dev

# Run tests
uv run pytest

# Run linter
uv run ruff check --fix

# See all CLI commands
causaganha --help
```

For detailed developer guidance, see [CLAUDE.md](CLAUDE.md).

## License

MIT
