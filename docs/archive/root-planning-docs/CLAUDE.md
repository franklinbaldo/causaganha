# CLAUDE.md

![Alpha](https://img.shields.io/badge/status-alpha-orange?style=for-the-badge)

> Development guidance for CausaGanha repository.

## Project Overview

**Mission:** Eliminate information asymmetry in the Brazilian legal market through transparent, data-driven lawyer performance ratings.

CausaGanha collects judicial communication data from the **DJEN API**, archives it on **Internet Archive**, and scores lawyer performance using the **OpenSkill** algorithm.

### Key Insight: Structured Data

DJEN provides **structured data** directly (lawyer names, OAB numbers, parties, case numbers). We don't need expensive LLM parsing - the API already gives us structured information about who is involved in each case.

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                      DATA PIPELINE                              │
└─────────────────────────────────────────────────────────────────┘

DJEN API (geo-blocked) → DJEN Proxy (Cloud Run, São Paulo)
                              │
                              ▼
                    GitHub Actions (5 min)
                    Download ZIP/Absent → Upload IA
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   INTERNET ARCHIVE                              │
│                                                                 │
│  djen-YYYY-MM-DD/                    ← One item per day         │
│  ├── djen-YYYY-MM-DD-TRIBUNAL.zip     ← Raw source (JSON)       │
│  ├── djen-YYYY-MM-DD-TRIBUNAL.absent  ← Empty journal marker    │
│  ├── comunicacoes.parquet             ← Consolidated (91 courts)│
│  ├── advogados.parquet                ← Lawyers (OAB+UF keyed)  │
│  ├── advogado_nomes.parquet           ← Lawyer name aliases     │
│  ├── representacoes.parquet           ← Lawyer-Party links      │
│  ├── processos.parquet                ← Process activity index  │
│  ├── textos.parquet                   ← Content-addressed texts │
│  ├── partes.parquet                   ← Normalized parties      │
│  └── classificacoes.parquet           ← Outcome labels          │
│                                                                 │
│  causaganha-catalog/                 ← Master catalog           │
│  ├── catalog.duckdb                                             │
│  ├── manifest.parquet                                           │
│  └── backfill-needed.parquet                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```text
src/causaganha/
├── cli/                 # Typer CLI (single entry point)
├── pipeline/            # Data orchestration (3-phase architecture)
│   ├── models.py        # Immutable dataclasses (ExportPlan, ExportResult)
│   ├── orchestration.py # Pure orchestration logic (testable)
│   ├── repositories.py  # Repository pattern for DB abstraction
│   ├── export_orchestrator.py # Main orchestrator (planning → execution → aggregation)
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
└── scripts/             # consolidate.py

.github/workflows/       # Automated pipelines
├── pipeline.yml         # Main data pipeline (single job, calls run.py)
└── test.yml             # CI/CD

scripts/
├── generate_catalog.py  # Catalog generation script
├── generate_dashboard_cache.py  # Dashboard cache generation
└── pipeline/            # Pipeline step scripts
    ├── run.py           # Orchestrator (pure functions + impure boundary)
    ├── collect.py       # Download from DJEN → upload ZIP/Absent to IA
    ├── consolidate.py   # Atomic ZIP → Parquet consolidation
    └── embed.py         # Generate embeddings
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

## Export Orchestrator Architecture

The export pipeline follows a **3-phase architecture** inspired by `scripts/pipeline/run.py`:

### Phase 1: Planning (Pure)
- `PureOrchestrator.plan_export()` - Build execution plan from inputs
- Validates dates and tribunal codes
- No I/O, fully testable

### Phase 2: Execution (Impure)
- `ExportOrchestrator._execute_tribunal_export()` - Execute per tribunal
- Export → Upload → Record
- Returns immutable `TribunalExportResult` objects

### Phase 3: Aggregation (Pure)
- `PureOrchestrator.aggregate_results()` - Combine results
- Computed properties: successful, failed, skipped, total_rows
- Returns immutable `ExportResult` dataclass

### Key Design Decisions

1. **Immutable State** - All results are frozen dataclasses, preventing state bugs
2. **Repository Pattern** - DB access via injected `ExportRepository` interface
   - `DuckDBExportRepository` - Production implementation
   - `MockExportRepository` - Testing without database
3. **Pure Functions** - Orchestration logic is testable without mocks
4. **Dependency Injection** - ExportOrchestrator receives repo + services

### Usage

```python
from causaganha.pipeline.repositories import DuckDBExportRepository
from causaganha.pipeline.export_orchestrator import ExportOrchestrator
from causaganha.pipeline.parquet_export import ParquetExporter
from causaganha.pipeline.ia_upload import InternetArchiveUploader

# Setup
db = get_connection()
repo = DuckDBExportRepository(db)
exporter = ParquetExporter(db, ExportConfig())
uploader = InternetArchiveUploader(UploadConfig())

# Create orchestrator with injected dependencies
orchestrator = ExportOrchestrator(repo, exporter, uploader)

# Execute (returns ExportResult, not dict)
result = await orchestrator.run_daily_export(date="2026-01-15")

# Access results via properties (not dict keys)
print(f"Successful: {result.successful}/{result.total_tribunals}")
print(f"Total rows: {result.total_rows:,}")
print(f"Failures: {result.failures}")

# Convert to dict for JSON serialization
result_dict = result.to_dict()
```

### Testing

Pure orchestration logic requires no database mocks:

```python
from causaganha.pipeline.orchestration import PureOrchestrator
from causaganha.pipeline.models import ExportPlan, TribunalExportResult

# Test pure functions directly
plan = PureOrchestrator.plan_export("2026-01-15", ("TJSP", "TJRJ"))
assert plan.partition_date == "2026-01-15"

# Test with mock repository
from causaganha.pipeline.repositories import MockExportRepository
repo = MockExportRepository(tribunals=("TJSP",))
```

## Internet Archive Structure

```text
djen-YYYY-MM-DD/                       ← Item per day
├── djen-YYYY-MM-DD-TRIBUNAL.zip       ← Raw JSON (source)
├── djen-YYYY-MM-DD-TRIBUNAL.absent    ← Completion marker
├── comunicacoes.parquet               ← Consolidated communications
├── advogados.parquet                  ← Global lawyer identifiers (OAB+UF)
├── advogado_nomes.parquet             ← Lawyer name aliases
├── representacoes.parquet             ← Materialized associations
├── processos.parquet                  ← Process activity index
├── textos.parquet                     ← Content-addressed judicial texts
├── partes.parquet                     ← Normalized party dimension
├── classificacoes.parquet             ← Outcome labels per text
└── destinatarios.parquet              ← Communication recipients

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
