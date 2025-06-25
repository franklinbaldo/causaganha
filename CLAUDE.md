# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CausaGanha is an automated judicial decision analysis platform that applies the Elo rating system (originally from chess) to evaluate lawyer performance in legal proceedings. It extracts, analyzes, and scores judicial decisions from the Tribunal de Justiça de Rondônia (TJRO) using Google's Gemini LLM.

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

# Extract content from PDF using Gemini
uv run python causaganha/core/extractor.py --pdf_file path/to/file.pdf

# Run complete pipeline (download → extract → update Elo ratings)
uv run python causaganha/core/pipeline.py run --date 2025-06-24

# Dry run (no actual changes)
uv run python causaganha/core/pipeline.py run --date 2025-06-24 --dry-run
```

## Architecture Overview

### Three-Stage Processing Pipeline

1. **Collection** (`downloader.py`): Downloads PDFs from TJRO
   - Handles redirect-based URL resolution
   - Uses proper headers to bypass bot protection
   - Saves files as `dj_YYYYMMDD.pdf` in `causaganha/data/diarios/`

2. **Extraction** (`extractor.py`): Processes PDFs with Gemini LLM
   - Uses Google Generative AI to parse PDF content
   - Extracts: process number, parties, lawyers, decision outcome
   - Outputs structured JSON to `causaganha/data/json/`

3. **Rating Update** (`elo.py` + `pipeline.py`): Applies Elo calculations
   - Matches lawyers from opposing sides
   - Updates ratings based on case outcomes (win/loss/draw)
   - Persists data in CSV files: `ratings.csv` and `partidas.csv`

### Key Modules

- **`pipeline.py`**: Main orchestrator with CLI commands (`collect`, `extract`, `update`, `run`)
- **`utils.py`**: Lawyer name normalization and decision validation utilities
- **`gdrive.py`**: Optional Google Drive integration for PDF backup
- **`elo.py`**: Pure Elo rating calculations (K-factor = 16, default rating = 1500)

### Data Flow

```
TJRO Website → PDF Download → Gemini Analysis → JSON Extraction → Elo Updates → CSV Storage
```

### File Organization

- `causaganha/core/`: Main business logic modules
- `causaganha/data/diarios/`: PDF files from TJRO
- `causaganha/data/json*/`: Extracted decision data in JSON format
- `causaganha/tests/`: Comprehensive unit test suite
- `.github/workflows/`: Automated CI/CD with 4 workflows (test, collect, extract, update)

## Testing Requirements

Per `AGENTS.md`: Always run `uv run pytest -q` before committing changes, even for documentation-only changes. The test suite includes:

- Mock-based tests for external API calls (Gemini, TJRO website)
- Elo calculation validation with known scenarios
- PDF download functionality with proper error handling
- JSON parsing and validation logic

## GitHub Actions Integration

Four automated workflows handle the complete pipeline:
1. `test.yml`: Runs tests, linting, and formatting checks
2. `01_collect.yml`: Daily PDF collection (cron: 5:00 UTC)
3. `02_extract.yml`: PDF content extraction using Gemini
4. `03_update.yml`: Elo rating updates and CSV commits

Requires these repository secrets:
- `GEMINI_API_KEY`
- `GDRIVE_SERVICE_ACCOUNT_JSON` (optional)
- `GDRIVE_FOLDER_ID` (optional)

## External Dependencies

- **Google Gemini API**: Core LLM for PDF content extraction
- **TJRO Website**: Source of judicial PDFs via redirect-based URLs
- **Google Drive API**: Optional backup storage for PDF files

The system is designed to be resilient to external service failures with proper error handling and dry-run capabilities for safe testing.