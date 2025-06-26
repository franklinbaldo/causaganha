# AGENTS Instructions

The scope of this file is the entire repository.

## Current System Architecture (2025-06-26)
CausaGanha is now a **distributed judicial analysis platform** with:
- **Async pipeline:** `src/async_diario_pipeline.py` for concurrent processing of 5,058 historical diários
- **Shared database:** DuckDB synchronized via Internet Archive with lock system
- **2-tier architecture:** Local DuckDB + Internet Archive (simplified from 4-tier)
- **4 specialized workflows:** pipeline.yml, bulk-processing.yml, database-archive.yml, test.yml

## Key Commands for Development
```bash
# Setup
uv venv && source .venv/bin/activate
uv sync --dev && uv pip install -e .

# Primary workflow (async pipeline)
uv run python src/async_diario_pipeline.py --max-items 5 --verbose --sync-database

# Database synchronization
uv run python src/ia_database_sync.py status
uv run python src/ia_database_sync.py sync

# Monitoring and discovery
uv run python src/ia_discovery.py --coverage-report --year 2025
uv run python src/async_diario_pipeline.py --stats-only

# Traditional CLI (still available)
causaganha pipeline run --date 2025-06-24
causaganha db status
```

## Testing Requirements
- **Always run** `uv run pytest -q` before committing any changes
- Dependencies managed by `uv` via `pyproject.toml` 
- Install with `uv sync --dev && uv pip install -e .[dev]`
- **Even for documentation-only changes, tests must be executed**
- Current test suite: 67+ tests with comprehensive API mocking

## Key Files and Architecture
- `src/async_diario_pipeline.py` - Main async processing pipeline
- `src/ia_database_sync.py` - Distributed database synchronization  
- `src/ia_discovery.py` - Internet Archive discovery and coverage analysis
- `data/causaganha.duckdb` - Shared database (synchronized via IA)
- `data/diarios_pipeline_ready.json` - 5,058 historical diários ready for processing
- `.github/workflows/` - 4 specialized workflows for different use cases

## Distributed System Considerations
- **Database locks:** System uses sentinel locks in Internet Archive to prevent conflicts
- **Concurrency:** Default 3 downloads + 2 uploads simultaneous (configurable)
- **Sync protocol:** Smart sync resolves conflicts automatically between PC and GitHub Actions
- **Rate limiting:** Built-in exponential backoff for external APIs (Gemini, TJRO)

## Commit messages
- Provide concise summaries describing the changes
- Reference the relevant files when summarizing your work in the PR description
- For distributed system changes, mention impact on sync/locks if relevant

