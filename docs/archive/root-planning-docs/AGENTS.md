# AGENTS Instructions

> 📋 **Primary Instructions**: For comprehensive coding agent instructions, development workflow, and plan-first approach, see **`CLAUDE.md`** - the primary source of truth for all AI coding assistants working with this repository.

The scope of this file is the entire repository.

## Current System Architecture (V2 - Active)

CausaGanha is a **distributed judicial analysis platform** currently under active construction (V2).

- **Core Package**: `src/causaganha/` (formerly `v2`)
- **Legacy Archive**: `legacy_archive/` (Broken/Deprecated V1 code)
- **Architecture**: Modular Monolith (API -> Pipeline -> Storage)

## Key Commands for Development

```bash
# Setup
uv sync --dev && uv pip install -e .

# Run CLI
uv run causaganha --help

# Run Tests
uv run pytest -v
```

## Testing Requirements

- **Always run** `uv run pytest` before committing any changes.
- All new code in `src/causaganha` must have corresponding tests in `tests/`.

## Key Files

- `src/causaganha/cli/` - Main CLI entry point (`__init__.py`)
- `src/causaganha/pipeline/` - Orchestration logic
- `src/causaganha/storage/` - Ibis/DuckDB adapter

## Commit messages

- Provide concise summaries describing the changes
- Reference the relevant files when summarizing your work in the PR description
