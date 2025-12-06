# Unified CLI Implementation

## Problem Statement

The current `causaganha` CLI has several stubbed commands (`queue`, `archive`, `analyze`, `score`). To fully realize the "Modern CLI Interface" described in `CLAUDE.md` and complete Phase 3 of the System Integration Resolution, these commands must be implemented to replace the legacy `pipeline.py` and `async_diario_pipeline.py` standalone usage.

## Proposed Solution

Implement the missing CLI commands in `src/cli.py` by integrating existing functionality from `async_diario_pipeline.py`, `extractor.py`, and `openskill_rating.py`.

### Technical Architecture

- **`queue` command**:
    - Adds URLs to the `job_queue` table.
    - Supports CSV input or direct URL.
    - Uses `src/utils.py` for URL validation and date extraction.
- **`archive` command**:
    - Wraps `async_diario_pipeline.py` logic.
    - Fetches "pending" items from `job_queue`.
    - Updates status to "downloaded" then "archived" (or "completed").
- **`analyze` command**:
    - Fetches "archived" (or "downloaded") items.
    - Uses `GeminiExtractor` to process PDFs.
    - Stores extraction results (JSON) path in metadata and updates status to "analyzed".
- **`score` command**:
    - Fetches "analyzed" items.
    - Parses JSON decisions.
    - Applies OpenSkill rating updates using `src/openskill_rating.py`.
    - Updates status to "scored".

## Implementation Plan

1.  **Refactor Utils**: Move URL and date helpers from `src/cli.py` to `src/utils.py`.
2.  **Test Utils**: Update `tests/test_utils.py`.
3.  **Implement `queue`**: Update `src/cli.py` and `tests/test_cli_commands.py`.
4.  **Implement `archive`**: Update `src/cli.py` to use `AsyncDiarioPipeline` with DB source.
5.  **Implement `analyze`**: Create logic to bridge DB items with `GeminiExtractor`.
6.  **Implement `score`**: Create logic to bridge DB items with scoring system.
7.  **Pre-commit**: Ensure all checks pass.
8.  **Submit**: Commit changes.

## Risks & Mitigations

- **Async Pipeline Integration**: Adapted by subclassing `AsyncDiarioPipeline` to update DB status.
- **Mocking complexity**: `test_analyze_command` required careful mocking of `requests` and `GeminiExtractor` due to import structures.
