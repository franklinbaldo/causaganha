# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CausaGanha is an automated judicial decision analysis platform that applies the TrueSkill rating system (developed by Microsoft Research) to evaluate lawyer performance in legal proceedings. It extracts, analyzes, and scores judicial decisions from the Tribunal de Justiça de Rondônia (TJRO) using Google's Gemini LLM.

## Development Setup

This project uses **uv** for dependency management (modern Python package manager):

```bash
# Install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
uv sync --dev
```

Environment variables (copy `.env.example` to `.env`):
- `GEMINI_API_KEY`: Required for PDF content extraction
- `GDRIVE_SERVICE_ACCOUNT_JSON`: Optional for PDF backup to Google Drive
- `GDRIVE_FOLDER_ID`: Google Drive folder ID for PDF storage

## Core Commands

### Testing & Quality
```bash
# Run all tests (required before commits)
uv run pytest -q

# Run specific test file
uv run pytest causaganha/tests/test_downloader.py -v

# Code formatting and linting
uv run ruff format
uv run ruff check
uv run ruff check --fix  # Auto-fix issues
```

### Pipeline Operations
```bash
# Download latest PDF from TJRO
uv run python causaganha/core/downloader.py --latest

# Download specific date
uv run python causaganha/core/downloader.py --date 2025-06-24

# Extract content from PDF using Gemini (with automatic rate limiting)
uv run --env-file .env python causaganha/core/extractor.py --pdf_file data/dj_20250624.pdf

# Run complete pipeline (download → extract → update TrueSkill ratings)
uv run python causaganha/core/pipeline.py run --date 2025-06-24

# Dry run (no actual changes)
uv run python causaganha/core/pipeline.py run --date 2025-06-24 --dry-run

# Migrate existing CSV/JSON data to DuckDB (one-time setup)
uv run python causaganha/core/migration.py

# Backup database to Cloudflare R2
uv run python causaganha/core/r2_storage.py backup

# Query remote snapshots without download
uv run python causaganha/core/r2_queries.py rankings --limit 10
```

## Architecture Overview

### Three-Stage Processing Pipeline

1. **Collection** (`downloader.py`): Downloads PDFs from TJRO
   - Handles redirect-based URL resolution
   - Uses proper headers to bypass bot protection
   - Saves files as `dj_YYYYMMDD.pdf` in `causaganha/data/diarios/`

2. **Extraction** (`extractor.py`): Processes PDFs with Gemini LLM using advanced chunking
   - **Text-based extraction**: Uses PyMuPDF for local PDF text extraction
   - **Smart chunking**: 25-page segments with 1-page overlap for context continuity
   - **Rate limiting**: Automatic exponential backoff respecting 15 RPM API limits
   - **Enhanced data**: Extracts process number, parties (polo ativo/passivo), lawyers with OAB, decision outcome, and 250-char summaries
   - **Robust output**: Structured JSON with automatic cleanup of intermediate files
   - **File organization**: Outputs to `data/` directory with consistent naming

3. **Rating Update** (`trueskill_rating.py` + `database.py`): Applies TrueSkill calculations
   - Forms teams of lawyers from opposing sides
   - Updates ratings (`mu` and `sigma`) based on case outcomes (win/loss/draw for teams)
   - Persists data in **DuckDB database**: unified storage for all system data
   - TrueSkill environment parameters are configured via `config.toml`.

### Key Modules

- **`pipeline.py`**: Main orchestrator with CLI commands (`collect`, `extract`, `update`, `run`)
- **`database.py`**: **NEW** - Unified DuckDB data layer for all system storage
- **`migration.py`**: **NEW** - Migration tools for CSV/JSON to DuckDB conversion
- **`trueskill_rating.py`**: TrueSkill rating calculations and environment setup
- **`config.toml`**: Configuration file for TrueSkill parameters
- **`utils.py`**: Lawyer name normalization and decision validation utilities
- **`gdrive.py`**: Optional Google Drive integration for PDF backup
- **`r2_storage.py`**: **NEW** - Cloudflare R2 storage for DuckDB snapshots and archival
- **`r2_queries.py`**: **NEW** - Direct DuckDB queries against R2-stored snapshots

### Data Flow

```
TJRO Website → PDF Download → Gemini Analysis → JSON Extraction → TrueSkill Updates → DuckDB Storage
                                                                                      ↓
                                                                        Cloudflare R2 Backup (Daily)
```

### Database Architecture

The system now uses **DuckDB** as the unified data storage layer, replacing scattered CSV files:

- **`data/causaganha.duckdb`**: Main database file with 5 core tables:
  - `ratings`: TrueSkill ratings (μ, σ) for each lawyer
  - `partidas`: Match history with team compositions and rating changes
  - `pdf_metadata`: PDF file tracking with SHA-256 hashes and Archive.org integration
  - `decisoes`: Extracted judicial decisions with validation status
  - `json_files`: Processing metadata for all JSON extraction files

- **Views and Analytics**: Built-in ranking views and statistics for system monitoring
- **Migration Support**: Automatic CSV/JSON to DuckDB conversion with backup creation
- **Cloud Backup**: Automated snapshots to Cloudflare R2 with compression and rotation

### File Organization

- `causaganha/core/`: Main business logic modules (Note: will move to `src/causaganha/core/` as per user's plan)
- `data/`: **Unified data directory** 
  - `data/causaganha.duckdb`: **Main database** - unified storage for all system data
  - `data/dj_YYYYMMDD.pdf`: PDF files from TJRO  
  - `data/dj_YYYYMMDD_extraction.json`: Extracted decision data (migrated to database)
  - `data/backup_pre_migration/`: Backup of original CSV files before DuckDB migration
- `tests/`: Comprehensive unit test suite (Note: will be at root level as per user's plan)
- `.github/workflows/`: Automated CI/CD with 4 workflows (test, collect, extract, update)

## Testing Requirements

Per `AGENTS.md`: Always run `uv run pytest -q` before committing changes, even for documentation-only changes. The test suite includes:

- Mock-based tests for external API calls (Gemini, TJRO website)
- TrueSkill calculation validation with known scenarios
- PDF download functionality with proper error handling
- JSON parsing and validation logic

## GitHub Actions Integration

Five automated workflows handle the complete pipeline:
1. `test.yml`: Runs tests, linting, and formatting checks
2. `01_collect.yml`: Daily PDF collection (cron: 5:00 UTC) 
3. `02_extract.yml`: PDF content extraction using Gemini
4. `03_update.yml`: TrueSkill rating updates and DuckDB storage
5. `04_backup_r2.yml`: **NEW** - Daily backup to Cloudflare R2 (cron: 7:00 UTC)

Requires these repository secrets:
- `GEMINI_API_KEY`
- `GDRIVE_SERVICE_ACCOUNT_JSON` (optional)
- `GDRIVE_FOLDER_ID` (optional)
- `CLOUDFLARE_ACCOUNT_ID` (for R2 backup)
- `CLOUDFLARE_R2_ACCESS_KEY_ID` (for R2 backup)
- `CLOUDFLARE_R2_SECRET_ACCESS_KEY` (for R2 backup)
- `CLOUDFLARE_R2_BUCKET` (optional, defaults to 'causa-ganha')

## External Dependencies

- **Google Gemini API**: Core LLM for PDF content extraction
  - **Model**: `gemini-2.5-flash-lite-preview-06-17` (as per `extractor.py`)
  - **Rate limits**: 15 RPM, 500 requests/day (Free tier) - Note: actual limits might vary.
  - **Features**: Text-based analysis with chunking and rate limiting
- **PyMuPDF (fitz)**: Local PDF text extraction library
- **TJRO Website**: Source of judicial PDFs via redirect-based URLs
- **Google Drive API**: Optional backup storage for PDF files
- **Cloudflare R2**: Primary cloud storage for DuckDB snapshots
  - **S3-compatible API**: Uses boto3 for seamless integration
  - **Compression**: zstandard compression for optimal storage efficiency
  - **Cost-effective**: ~$0.05/month for typical usage
  - **Remote queries**: DuckDB can query R2 snapshots directly

The system is designed to be resilient to external service failures with proper error handling, exponential backoff, and dry-run capabilities for safe testing.