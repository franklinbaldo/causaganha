# CLAUDE.md

![Alpha](https://img.shields.io/badge/status-alpha-orange?style=for-the-badge)

> ⚠️ **ALPHA SOFTWARE**: Active V2 Development.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚀 V2 Construction Mode

**CausaGanha is currently building V2**. V1 has been archived to `legacy_archive/` as it was non-functional.

### Directory Structure

```
src/causaganha/       # Main package (Canonical V2)
├── cli.py           # Main CLI entry point
├── api/             # PJe API client (httpx + Pydantic)
├── storage/         # Ibis + DuckDB data layer
├── analysis/        # Pydantic AI decision analyzer
├── pipeline/        # Orchestration (collect, analyze, score)
└── utils/           # Structured logging
legacy_archive/      # Archived V1 code (Do not use)
```

## 📖 Project Overview

**Mission:** Eliminate information asymmetry in the Brazilian legal market through transparent, data-driven lawyer performance ratings.

CausaGanha is an automated judicial decision analysis platform. It extracts, analyzes, and scores judicial decisions from Brazilian tribunals using Google's Gemini LLM with local DuckDB storage.

**For complete project understanding, see:**
- [`docs/PRODUCT_VISION.md`](docs/PRODUCT_VISION.md) - Product strategy, user personas, and success metrics
- [`docs/MVP_SCOPE.md`](docs/MVP_SCOPE.md) - Current development scope and definition of "done"
- [`docs/ROADMAP.md`](docs/ROADMAP.md) - Feature prioritization and timeline
- [`docs/TECHNICAL_REQUIREMENTS.md`](docs/TECHNICAL_REQUIREMENTS.md) - Scale targets and performance specs
- [`docs/COMPLIANCE.md`](docs/COMPLIANCE.md) - Legal and regulatory requirements (LGPD, OAB)

## Development Setup

```bash
uv venv
source .venv/bin/activate
uv sync --dev
uv pip install -e .
```

## Development Flow

CausaGanha follows a **plan-first development approach**:

### 📋 **Phase 1: Planning**

1. **Create Plan Document**: New features must start as a plan in `/docs/plans/feature-name.md`
2. **Problem Context**: Explain the problem, solution, and steps.

### 🚀 **Phase 2: Implementation**

1. **Test-Driven**: Create tests in `tests/` first.
2. **Implement**: Code in `src/causaganha/`.
3. **Verify**: Run `uv run pytest`.

## Core Commands (V2)

```bash
# Run CLI
uv run causaganha --help

# Run tests
uv run pytest

# Run BDD feature tests
uv run pytest tests/features/

# Run specific priority features
uv run pytest tests/features/01_*.feature  # Priority 1
uv run pytest tests/features/02_*.feature  # Priority 2
```

## 🧪 Testing Strategy

CausaGanha has comprehensive BDD (Behavior-Driven Development) test coverage:

- **329+ scenarios** across **10+ feature files** (core functionality)
- **100+ scenarios** for parquet analysis (schema v2 + advanced workflows)
- **Hierarchical organization** by business priority (P1-P4)
- **Living documentation** that serves as both spec and test

See [`tests/features/README.md`](tests/features/README.md) for the complete BDD suite and feature hierarchy.

### Parquet Analysis Features

- **Schema v2**: 5 feature files in `tests/features/parquet_schema_v2/`
- **Advanced**: 6 feature files in `tests/features/parquet_advanced/` (89 scenarios)
  - Incremental reprocessing (fix historical errors)
  - DuckDB remote queries (query IA directly)
  - Data quality monitoring (automated validation)
  - Vector store hydration (load embeddings from IA)
  - Time-travel queries (historical comparison)
  - Cross-tribunal analytics (national insights)

## Architecture Overview

**Style**: Modular Monolith (Hexagonal-ish).

*   **Domain**: `src/causaganha/analysis` (Pure logic)
*   **Application**: `src/causaganha/pipeline` (Orchestration)
*   **Infrastructure**: `src/causaganha/storage` (Ibis), `src/causaganha/api` (HTTP)

## 📦 Parquet-Based Analysis Architecture

CausaGanha uses a **multi-parquet architecture** for data storage and analysis, with files hosted on Internet Archive.

### Architecture Overview

```
Internet Archive Storage:
├── causaganha-decisions-YYYY-MM-DD-TRIBUNAL.parquet   ← Decision text, analysis (NO embeddings!)
├── causaganha-embeddings-YYYY-MM-DD-TRIBUNAL.parquet ← Embeddings ONLY! (separate file)
├── causaganha-lawyers-YYYY-MM-DD.parquet              ← Lawyer profiles and ratings
└── causaganha-partes-YYYY-MM-DD-TRIBUNAL.parquet      ← Case parties information

Join Key: intimation_id (consistent across all files)
Query Engine: DuckDB (columnar joins at query time)
```

### Key Design Principles

1. **Separation of Concerns**: Each entity type in separate parquet file
2. **Texto-Based Analysis**: Use `intimations.texto` field, NOT PDFs
3. **Embeddings Separate**: Enables regeneration without touching decisions
4. **DuckDB Joins**: Efficient columnar joins at query time (no duplication)
5. **Internet Archive**: Free, unlimited storage for all parquet exports

### Available Workflows

```bash
# Download parquet from Internet Archive
uv run causaganha parquet download --tribunal TJRO --date 2025-01-15

# Analyze decisions from local parquet
uv run causaganha parquet analyze --file decisions-2025-01-15-TJRO.parquet

# Analyze directly from Internet Archive
uv run causaganha parquet analyze-ia --tribunal TJRO --date 2025-01-15

# Check if parquet exists on IA
uv run causaganha parquet check --tribunal TJRO --date 2025-01-15

# Clear local parquet cache
uv run causaganha parquet clear-cache
```

### DJEN Parquet Structure (Raw API Data)

**Internet Archive items** (e.g., `djen-parquet-2026-01-21-TRF4`) contain **6 normalized parquet files** scraped from the PJe DJEN API:

```
djen-parquet-YYYY-MM-DD-TRIBUNAL/
├── comunicacoes.parquet          # Main communication metadata (~260K rows)
│   └── Columns: id, numero_processo, tribunal, data_disponibilizacao,
│                orgao, tipo, classe, numero_comunicacao, status
│
├── textos.parquet                # Full text content (~246K rows)
│   └── Columns: texto_id, texto, tamanho
│
├── partes.parquet                # Party master table (~211K parties)
│   └── Columns: parte_id (UUID), nome, documento (CPF/CNPJ)
│
├── comunicacao_partes.parquet    # Party-communication associations (~370K links)
│   └── Columns: comunicacao_id, parte_id, papel
│       - papel: "A" (Ativo/Author), "P" (Passivo/Defendant), "T" (Terceiro), etc.
│
├── advogados.parquet             # Lawyer master table
│   └── Columns: advogado_id (UUID), nome, oab_numero, oab_uf
│
└── comunicacao_advogados.parquet # Lawyer-communication associations
    └── Columns: comunicacao_id, advogado_id
```

**How to JOIN for party information:**

```python
import pyarrow.parquet as pq
import pandas as pd

# Load tables
comunicacoes = pq.read_table('comunicacoes.parquet').to_pandas()
partes = pq.read_table('partes.parquet').to_pandas()
comunicacao_partes = pq.read_table('comunicacao_partes.parquet').to_pandas()

# Get parties for a specific comunicacao
result = (
    comunicacao_partes[comunicacao_partes['comunicacao_id'] == '502461475']
    .merge(partes, on='parte_id')
)

# Result example:
#   papel  | nome
#   -------|---------------------------------
#   A      | ELIANE DIAS
#   P      | BANCO MASTER S/A
```

**Key insight:** Party data (autor, réu) is **already structured and normalized** in separate parquet files. No HTML parsing needed!

### Documentation

- **Architecture**: [`docs/SCHEMA_V2_FINAL_RECOMMENDATIONS.md`](docs/SCHEMA_V2_FINAL_RECOMMENDATIONS.md) - Multi-parquet design
- **Implementation**: [`docs/plans/parquet-analysis-adaptation.md`](docs/plans/parquet-analysis-adaptation.md) - Parquet pipeline
- **Texto vs PDF**: [`docs/TEXTO_VS_PDF_CLARIFICATION.md`](docs/TEXTO_VS_PDF_CLARIFICATION.md) - Why texto, not PDFs
- **BDD Specs**: [`tests/features/parquet_schema_v2/README.md`](tests/features/parquet_schema_v2/README.md) - Schema v2 features
- **Advanced Features**: [`tests/features/parquet_advanced/`](tests/features/parquet_advanced/) - 89 scenarios for advanced workflows

### Important: Texto-Based Analysis

**Analysis uses the `texto` field, NOT PDFs!**

```python
# ✅ CORRECT: Use texto field
llm_result = await self.llm.analyze_text(texto, intimation_id)

# ❌ WRONG: Don't use PDFs
# llm_result = await self.llm.analyze_pdf(pdf_url, intimation_id)  # DEPRECATED
```

The `analyze_pdf()` method is deprecated. All analysis should use `analyze_text()` with the texto field.

## 🧠 Embedding Providers

CausaGanha supports multiple embedding providers with **automatic provider selection** based on API key availability and authentication.

### Available Providers

1. **Jina AI** (Priority #1)
   - Model: `jina-embeddings-v3`
   - Dimensions: 1024 (configurable 256-1024)
   - API Key: `JINA_API_KEY` environment variable (already configured in GitHub secrets)
   - Best for: Multilingual support, Matryoshka embeddings, cost efficiency

2. **Google Gemini** (Priority #2, Fallback)
   - Model: `text-embedding-004`
   - Dimensions: 768
   - API Key: `GOOGLE_API_KEY` environment variable
   - Best for: General-purpose embeddings with Google's ecosystem

### Auto-Selection (Recommended)

By default, CausaGanha automatically selects the best available provider:

1. Checks for `JINA_API_KEY` first (priority #1)
2. Validates the API key by attempting authentication
3. Falls back to `GOOGLE_API_KEY` if Jina is unavailable
4. Throws an error if no valid provider is found

This ensures the system always uses the best available option without manual configuration.

### Configuration

Set the provider in your `.env` file:

```bash
# Auto-select (default, recommended)
EMBEDDING_PROVIDER=auto
EMBEDDING_PROVIDER_PRIORITY=jina,google  # Try Jina first, then Google

# OR manually specify a provider
EMBEDDING_PROVIDER=google  # Force Google
EMBEDDING_PROVIDER=jina    # Force Jina

# Set your API keys
JINA_API_KEY=your_jina_api_key
GOOGLE_API_KEY=your_google_api_key
```

### Usage

```python
from causaganha.v2.analysis.embedding_service import EmbeddingService

# Auto-select best available provider (recommended)
service = await EmbeddingService.create()  # async factory method

# Auto-select with custom priority
service = await EmbeddingService.create(priority=["google", "jina"])

# Use specific provider
service = EmbeddingService(provider="jina")  # synchronous

# Generate embeddings
embedding = await service.embed_text("Your text here")
```

### How Auto-Selection Works

1. **API Key Check**: Verifies environment variables exist
2. **Authentication Test**: Makes a test API call to validate credentials
3. **Priority Order**: Tries providers in configured priority order
4. **Fallback**: Automatically falls back to next provider if one fails
5. **Logging**: Comprehensive logs for debugging provider selection

### Implementation

- **Provider abstraction**: `src/causaganha/v2/analysis/embedding_providers.py`
- **Auto-selection logic**: `auto_select_provider()` function
- **Service wrapper**: `src/causaganha/v2/analysis/embedding_service.py`
- **Configuration**: `src/causaganha/config.py`

## 🤖 **Agent Registry System**

CausaGanha implements a parallel development system using an agent registry in `.agents/`.
See `.agents/README.md` for detailed communication guidelines.

## 🤖 **Jules Automation System**

CausaGanha uses the Jules automation system for autonomous code maintenance and improvement.
The system consists of AI personas (agents) that work on the codebase autonomously.

**Key components:**
- `.team/` - Jules scheduler and persona configurations
- `.team/personas/` - AI agent definitions with specialized roles
- `.team/README.md` - Complete Jules system documentation

**Available commands:**
```bash
# Run a specific persona
uv run jules schedule tick --prompt-id <persona-name>

# Run the scheduler
uv run jules schedule tick

# Check persona mailbox
uv run mail inbox --persona <persona-name>@team
```

For complete documentation, see [.team/README.md](.team/README.md).
