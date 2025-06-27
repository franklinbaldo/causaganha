# CLAUDE.md

![Alpha](https://img.shields.io/badge/status-alpha-orange?style=for-the-badge)
![Breaking Changes](https://img.shields.io/badge/breaking_changes-expected-red?style=for-the-badge)
![No Backwards Compatibility](https://img.shields.io/badge/backwards_compatibility-none-critical?style=for-the-badge)

> ⚠️ **ALPHA SOFTWARE**: This project is in active development with frequent breaking changes. APIs, database schemas, and core functionality may change without notice or backwards compatibility. Use at your own risk in production environments.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CausaGanha is an automated judicial decision analysis platform that applies the OpenSkill rating system to evaluate lawyer performance in legal proceedings. It extracts, analyzes, and scores judicial decisions from Brazilian tribunals using Google's Gemini LLM with a shared database architecture hosted on Internet Archive.

## Development Setup

This project uses **uv** for dependency management and follows modern Python packaging standards:

```bash
# Install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
uv sync --dev
uv pip install -e .  # Install package in development mode
```

Environment variables (copy `.env.example` to `.env`):
- `GEMINI_API_KEY`: Required for PDF content extraction
- `IA_ACCESS_KEY`: Required for Internet Archive uploads and database sync
- `IA_SECRET_KEY`: Required for Internet Archive uploads and database sync

## Core Commands

### Modern CLI (Primary Interface)

CausaGanha now provides a modern, user-friendly CLI for judicial document processing:

```bash
# Queue URLs from CSV file
uv run --env-file .env causaganha queue --from-csv diarios.csv

# Download and archive to Internet Archive
uv run --env-file .env causaganha archive --limit 10

# Extract information using Gemini LLM
uv run --env-file .env causaganha analyze --limit 5

# Calculate OpenSkill ratings
uv run --env-file .env causaganha score

# Run full pipeline in one command
uv run --env-file .env causaganha pipeline --from-csv diarios.csv

# Monitor progress and statistics
uv run --env-file .env causaganha stats

# Database management
uv run --env-file .env causaganha db status
uv run --env-file .env causaganha db migrate
uv run --env-file .env causaganha db sync
```

### Legacy Async Pipeline (Advanced Users)

For advanced users, the original async pipeline is still available:

```bash
# Legacy async pipeline commands
uv run --env-file .env python src/async_diario_pipeline.py --max-items 5 --sync-database --upload-database
```

### Database Synchronization

Shared database system with Internet Archive for cross-platform collaboration:

```bash
# Check database sync status
uv run --env-file .env python src/ia_database_sync.py status

# Smart sync (automatically choose download/upload)
uv run --env-file .env python src/ia_database_sync.py sync

# Download latest database from IA
uv run --env-file .env python src/ia_database_sync.py download

# Upload local changes to IA
uv run --env-file .env python src/ia_database_sync.py upload

# Force operations (bypass locks)
uv run --env-file .env python src/ia_database_sync.py sync --force
```

### Internet Archive Discovery

Tools for discovering and analyzing uploaded diarios:

```bash
# List uploaded diarios for specific year
uv run --env-file .env python src/ia_discovery.py --year 2025

# Coverage analysis (what's missing vs expected)
uv run --env-file .env python src/ia_discovery.py --coverage-report

# Export complete inventory
uv run --env-file .env python src/ia_discovery.py --export inventory.json

# Check specific item exists
uv run --env-file .env python src/ia_discovery.py --check-identifier tjro-diario-2025-06-26
```

### Testing & Quality
```bash
# Run all tests (required before commits)
uv run pytest -q

# Run specific test file
uv run pytest tests/test_downloader.py -v

# Code formatting and linting
uv run ruff format
uv run ruff check
uv run ruff check --fix  # Auto-fix issues
```

## Architecture Overview

### Distributed Database System

CausaGanha uses a **shared database architecture** hosted on Internet Archive, enabling seamless collaboration between local development and automated GitHub Actions:

- **Shared Storage**: Single DuckDB database on IA (`causaganha-database-live`)
- **Cross-Platform**: Works from any environment (Windows, Linux, macOS)
- **Conflict Prevention**: Lock-based system prevents concurrent access issues
- **Automatic Sync**: Smart sync determines when to upload/download changes

### Four-Stage Data Lifecycle Pipeline

**Modern CLI Interface**: Primary user interface with `causaganha` command providing intuitive access to all pipeline stages.

**Pipeline Stages**:

1. **Queue** (`causaganha queue`): Add judicial documents to processing queue
   - **Flexible Input**: URLs or CSV files with automatic tribunal detection
   - **Domain Validation**: Only .jus.br domains accepted for security
   - **Smart Detection**: Auto-extract date and metadata from URLs

2. **Archive** (`causaganha archive`): 
   - **Concurrent Processing**: Downloads multiple PDFs simultaneously from TJRO
   - **Internet Archive Upload**: Direct upload to IA with metadata preservation
   - **Original Filename Preservation**: Maintains authentic TJRO naming (e.g., `20250626614-NR115.pdf`)
   - **Progress Tracking**: Resume capability with persistent progress files
   - **Rate Limiting**: Respectful to TJRO servers (3 concurrent downloads max)

3. **Analyze** (`causaganha analyze`): 
   - **Gemini LLM Processing**: Uses Google's Gemini 2.5 Flash for content analysis
   - **Chunked Processing**: 25-page segments with 1-page overlap for context
   - **Temporary Files**: All processing artifacts in temp directories (no data pollution)
   - **Enhanced Data**: Extracts process numbers, parties, lawyers with OAB, outcomes
   - **JSON Output**: Structured data with automatic validation

4. **Score** (`causaganha score`):
   - **OpenSkill Algorithm**: Advanced rating system for skill assessment
   - **Team Formation**: Lawyers grouped by case sides (polo ativo/passivo)
   - **Database Storage**: All data unified in DuckDB format
   - **Shared Updates**: Changes automatically synced to IA for global access

### Key Modules

#### Modern CLI Interface
- **`cli.py`**: **NEW** - Modern Typer-based CLI with 4-stage pipeline
  - Queue, Archive, Analyze, Score commands with rich progress display
  - Database management (migrate, status, sync, backup, reset)
  - Pipeline orchestration with resume capability and error handling
  - .jus.br domain validation and smart metadata extraction

#### Core Processing
- **`async_diario_pipeline.py`**: **NEW** - Main async pipeline with concurrent processing
- **`ia_database_sync.py`**: **NEW** - Shared database synchronization with locking
- **`ia_discovery.py`**: **NEW** - Tools for discovering uploaded content in IA
- **`extractor.py`**: Gemini-powered content extraction with temp file handling
- **`openskill_rating.py`**: OpenSkill rating calculations and environment setup

#### Data Management
- **`database.py`**: **NEW** - Unified DuckDB data layer for all system storage
- **`diario_processor.py`**: **NEW** - Convert raw TJRO data to pipeline-ready format
- **`utils.py`**: Lawyer name normalization and decision validation utilities
- **`config.py`**: Configuration management with TOML support

#### Legacy Integration
- **`pipeline.py`**: Legacy orchestrator (use async_diario_pipeline.py instead)
- **`downloader.py`**: Individual PDF downloads (integrated into async pipeline)

### Complete Data Architecture

The system implements a **simplified 2-tier storage strategy** for optimal performance and cost:

#### Tier 1: Local DuckDB (Development & Processing)
- **`data/causaganha.duckdb`**: Main database file with unified schema
- **Core Tables**: ratings, partidas, decisoes, pdf_metadata, json_files
- **High Performance**: Local access for development and processing

#### Tier 2: Internet Archive (Shared & Permanent Storage)
- **Shared Database**: `causaganha-database-live` for cross-platform collaboration
- **PDF Archive**: All diarios permanently stored with proper metadata
- **Public Access**: Complete transparency with research-friendly URLs
- **Zero Cost**: Free permanent storage with global CDN
- **Lock System**: Prevents concurrent access conflicts

### Data Flow

```
TJRO Website → Async Download → Internet Archive → Gemini Analysis → TrueSkill Updates → Shared Database
                     ↓              ↓                   ↓                  ↓              ↓
                Original Names   Public Archive      JSON Extraction    Rating Updates   IA Sync
                     ↓              ↓                   ↓                  ↓              ↓
               Progress Tracking  Permanent Storage   Temp Processing   Local DuckDB    Cross-Platform
```

### File Organization

- **`src/`**: **Main modules** - Flatter Python src-layout structure
  - `async_diario_pipeline.py`: **NEW** - Primary async processing pipeline
  - `ia_database_sync.py`: **NEW** - Shared database synchronization
  - `ia_discovery.py`: **NEW** - IA content discovery and analysis
  - `diario_processor.py`: **NEW** - Data format conversion utilities
  - `extractor.py`: Gemini-powered content extraction
  - `database.py`: DuckDB data layer operations
  - All other core modules directly in src/
- **`tests/`**: **Unified test suite** - All tests in one location
  - Comprehensive unit tests with pytest configuration
  - Mock-based tests for external API calls
  - Coverage reporting for src/ modules
- **`data/`**: **Unified data directory** 
  - `data/causaganha.duckdb`: **Main database** - synced with IA
  - `data/diarios_pipeline_ready.json`: **NEW** - 5,058 diarios ready for processing
  - `data/todos_diarios_tjro.json`: **NEW** - Complete TJRO diario list (2004-2025)
  - `data/diarios_2025_only.json`: **NEW** - Filtered current year for testing
  - `data/diarios/`: Downloaded PDFs with original TJRO filenames
- **`.github/workflows/`**: **Automated CI/CD** with **4 modern workflows**
  - `pipeline.yml`: **NEW** - Daily async pipeline with database sync
  - `bulk-processing.yml`: **NEW** - Large-scale processing with multiple modes
  - `database-archive.yml`: Weekly/monthly database snapshots to IA
  - `test.yml`: Quality assurance with comprehensive testing

## Testing Requirements

Per `AGENTS.md`: Always run `uv run pytest -q` before committing changes. The test suite includes:

- Mock-based tests for external API calls (Gemini, TJRO website, IA)
- TrueSkill calculation validation with known scenarios
- Async pipeline functionality with proper error handling
- Database synchronization and locking mechanisms
- JSON parsing and validation logic

## GitHub Actions Integration

**Four automated workflows** handle the complete data lifecycle with shared database support:

#### 1. Daily Async Pipeline (`pipeline.yml`)
- **Daily at 03:15 UTC** - Processes latest 5 diarios automatically
- **Manual dispatch** - Flexible date ranges, item limits, force reprocessing
- **Database sync** - Downloads latest before processing, uploads changes after
- **Comprehensive reporting** - Statistics, IA discovery, progress tracking

#### 2. Bulk Processing (`bulk-processing.yml`) ⭐ **NEW**
- **On-demand processing** - Handle large-scale operations (up to all 5,058 diarios)
- **Multiple modes**: year_2025, year_2024, last_100, last_500, all_diarios, custom_range
- **Concurrency tuning** - Configurable download/upload limits
- **6-hour timeout** - Handles massive processing jobs
- **Full database sync** - Ensures consistency across environments

#### 3. Database Archive (`database-archive.yml`)
- **Weekly on Sunday at 04:00 UTC** - Database snapshots to IA
- **Monthly archives** - First Sunday of each month (permanent retention)
- **Public research** - Makes complete TrueSkill datasets publicly available
- **Deduplication** - Skips upload if archive already exists

#### 4. Quality Assurance (`test.yml`)
- **On PR/Push** - Comprehensive testing with all core components
- **Auto-formatting** - Automatic ruff formatting and linting
- **Coverage reporting** - Ensures code quality standards

**Required repository secrets:**
- `GEMINI_API_KEY` (required for PDF extraction)
- `IA_ACCESS_KEY` (required for Internet Archive operations)
- `IA_SECRET_KEY` (required for Internet Archive operations)

## External Dependencies

- **Google Gemini API**: Core LLM for PDF content extraction
  - **Model**: `gemini-2.5-flash-lite-preview-06-17`
  - **Rate limits**: 15 RPM with automatic backoff
  - **Features**: Chunked analysis with overlap for context continuity
- **PyMuPDF (fitz)**: Local PDF text extraction library
- **TJRO Website**: Source of judicial PDFs via direct download URLs
- **Internet Archive**: 
  - **Primary storage**: All PDFs and shared database
  - **Public access**: Permanent URLs for transparency
  - **Lock system**: Conflict prevention for concurrent operations
  - **CLI tools**: Uses `ia` command-line tool for operations
- **DuckDB**: High-performance embedded database for all data storage
- **aiohttp**: Async HTTP operations for concurrent processing

## System Overview & Achievements

### 🎯 Alpha Distributed Solution
CausaGanha has evolved into an **alpha-stage, distributed judicial analysis platform** with:

#### ✅ **Shared Database Architecture**
- **Cross-Platform Collaboration**: Same database accessible from any environment
- **Conflict Prevention**: Lock-based system prevents concurrent access issues  
- **Automatic Synchronization**: Smart sync determines when to upload/download
- **Internet Archive Hosting**: Zero-cost, permanent, globally accessible storage

#### ✅ **Async Processing Pipeline**
- **Concurrent Operations**: Process multiple diarios simultaneously 
- **Original Filename Preservation**: Maintains authentic TJRO naming conventions
- **Progress Tracking**: Resume capability for interrupted processing
- **Temporary File Handling**: Clean separation of processing vs permanent data

#### ✅ **Comprehensive Discovery System**
- **Coverage Analysis**: Track what's uploaded vs what should exist
- **Inventory Management**: Export complete catalogs of processed content
- **Public Transparency**: All judicial records publicly accessible via IA

#### ✅ **Advanced GitHub Actions**
- **4 specialized workflows** with shared database integration
- **Bulk processing** capabilities for massive datasets (5,058+ diarios)
- **Automatic conflict resolution** through distributed locking
- **Comprehensive reporting** with statistics and discovery tools

#### ✅ **Alpha Quality Features**
- **60+ unit tests** with comprehensive mocking of external APIs
- **Database synchronization** tested with real IA integration
- **Lock timeout handling** ensures no permanent deadlocks
- **Error recovery** with exponential backoff and retry logic
- **⚠️ Breaking changes expected**: Core APIs and data structures may change

### 🚀 **Operational Excellence**
The system demonstrates **enterprise-grade distributed architecture** with:
- **Multi-environment access**: Development and automation share same data
- **Zero data loss**: Lock system prevents corruption from concurrent access
- **Automatic scaling**: Handles datasets from single items to 21+ years of records
- **Cost optimization**: Leverages free IA storage for massive datasets
- **Global accessibility**: Public transparency through permanent IA URLs

### 🎖️ **Technical Innovation**
- **Distributed database**: First-of-its-kind shared DuckDB via Internet Archive
- **Async judicial processing**: Concurrent analysis of legal documents at scale
- **Original filename preservation**: Maintains archival authenticity
- **Lock-based conflict resolution**: Prevents distributed system race conditions

The system processes judicial records from 2004-2025 (21+ years) with complete automation, cross-platform collaboration, and public transparency.

## ⚠️ Alpha Status Warning

**CausaGanha is ALPHA software** with the following implications:

- **Breaking Changes**: Core APIs, CLI commands, and database schemas may change without notice
- **No Backwards Compatibility**: Updates may require complete data migration or reinstallation
- **Experimental Features**: New functionality may be added, modified, or removed rapidly
- **API Instability**: Function signatures, return types, and behavior may change
- **Data Format Changes**: Database schema and file formats may evolve incompatibly
- **Configuration Changes**: Settings and environment variables may be restructured

**Use in production at your own risk.** Consider this software experimental and expect to adapt to breaking changes.

---

**Status: 🔶 ALPHA DISTRIBUTED** - Experimental shared database architecture (2025-06-27): cross-platform collaboration, conflict prevention, async processing, and comprehensive automation. Alpha-stage distributed judicial analysis platform with breaking changes expected.