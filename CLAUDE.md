# CLAUDE.md

![Alpha](https://img.shields.io/badge/status-alpha-orange?style=for-the-badge)

> ⚠️ **ALPHA SOFTWARE**: Modern Structured Data Ingestion via DJEN.

This file provides guidance for development in this repository.

## 🚀 Canonical Architecture

CausaGanha has consolidated into a modular monolith focused on structured data ingestion from the DJEN API.

### Directory Structure

```text
src/causaganha/       # Main package
├── cli/             # Typer CLI commands
├── api/             # DJEN API integration (Structured data)
├── storage/         # Ibis + DuckDB + Parquet data layer
├── analysis/        # Decision classification (ML/Heuristics)
├── pipeline/        # Orchestration (scrape, normalize, rate)
├── scoring/         # OpenSkill rating system
└── config.py        # Settings and environment
djen-scraper/        # Cloudflare Worker for continuous scraping
```

## 📖 Project Overview

**Mission:** Eliminate information asymmetry in the Brazilian legal market through transparent, data-driven lawyer performance ratings.

CausaGanha ingests structured judicial communication data from the **Diário de Justiça Eletrônico Nacional (DJEN)**, normalizes it into Parquet tables stored on the **Internet Archive**, and scores lawyer performance using the **OpenSkill** algorithm.

### Key Shift: Structured Data vs. LLMs

We no longer rely on expensive LLM analysis of decision texts. We leverage the **structured data** provided directly by the DJEN API (lawyer names, OABs, process numbers, and communication types).

## Development Setup

```bash
uv venv
source .venv/bin/activate
uv sync --dev
uv pip install -e .
```

## Core Commands

```bash
# Run CLI
causaganha --help

# Database management
causaganha db init
causaganha db status

# Pipeline execution
causaganha pipeline --help
```

## 🧪 Testing Strategy

- **Test-Driven**: Create tests in `tests/` first.
- **Run tests**: `uv run pytest`
- **BDD Features**: `uv run pytest tests/features/`

## 📦 Data Architecture

CausaGanha uses a **multi-parquet architecture** for data storage, with files hosted on Internet Archive.

```text
Internet Archive Storage:
├── djen-parquet-YYYY-MM-DD-TRIBUNAL.parquet   ← Main communications (Structured)
├── djen-lawyers-YYYY-MM-DD.parquet              ← Lawyer profiles and ratings
└── djen-partes-YYYY-MM-DD-TRIBUNAL.parquet      ← Case parties information
```

**Query Engine**: DuckDB (columnar joins at query time).
