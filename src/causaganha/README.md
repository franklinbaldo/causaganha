# CausaGanha - Package Architecture

This directory contains the main CausaGanha package.

## Directory Structure

```
src/causaganha/
├── cli/                  # Typer CLI commands
│   └── __init__.py      # Main CLI application
├── api/                  # External API clients (if needed)
├── storage/             # Ibis + DuckDB data layer
│   ├── connection.py    # DuckDB connection via Ibis (singleton)
│   ├── schema.sql       # Table definitions
│   ├── queries.py       # Data access queries
│   └── migrations.py    # Schema migrations
├── analysis/            # Decision analysis (AI + embeddings)
│   ├── analyzer.py      # Pydantic AI decision analyzer
│   ├── rag_analyzer.py  # RAG-based analyzer
│   ├── hybrid_analyzer.py # Hybrid strategy (RAG + LLM fallback)
│   ├── embedding_service.py # Embedding generation
│   ├── vector_store.py  # LanceDB vector storage
│   └── models.py        # DecisionAnalysis Pydantic models
├── pipeline/            # Data pipeline orchestration
│   ├── collect.py       # Metadata collection from DJEN
│   ├── analyze.py       # Decision analysis workflow
│   ├── analyze_parquet.py # Parquet-based analysis
│   ├── parquet_export.py # Export to Parquet format
│   ├── ia_upload.py     # Internet Archive upload
│   ├── ia_download.py   # Internet Archive download
│   ├── export_orchestrator.py # Export workflow orchestration
│   └── score.py         # OpenSkill rating calculation
├── scoring/             # OpenSkill rating system
│   └── openskill.py     # Rating algorithm wrapper
├── catalog/             # DuckDB metadata catalog
│   └── creator.py       # Catalog creation for remote Parquet
├── clients/             # External service clients
│   └── archive.py       # Internet Archive client
└── config.py            # Pydantic Settings configuration
```

## Technology Stack

- **Pydantic AI**: LLM provider abstraction with structured outputs
- **Ibis Framework**: Fast analytical queries via DuckDB
- **DuckDB**: Embedded analytical database
- **LanceDB**: Vector storage for embeddings
- **httpx/aiohttp**: Async HTTP clients
- **structlog**: Structured logging
- **OpenSkill**: Lawyer rating algorithm
- **Internet Archive**: Data distribution platform

## Data Flow

```
DJEN API → Metadata (structured JSON)
    ↓
Store in DuckDB + Parquet
    ↓
Pydantic AI + Gemini → Analyze decisions → Extract outcomes
    ↓
OpenSkill → Calculate ratings
    ↓
Internet Archive → Publish data + rankings
```
