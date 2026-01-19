# CausaGanha V2 Migration Plan

## Context
The project is currently in a hybrid state. V2 core components (`src/causaganha/v2/`) are implemented but not integrated into the main application entry point (`src/causaganha/cli.py`), which still uses V1 components.

## Objectives
1.  Complete V2 functionality (add Archive pipeline).
2.  Migrate the CLI to use V2 pipelines exclusively.
3.  Ensure E2E tests verify the V2 architecture.

## Detailed Plan

### 1. Implement V2 Archive Pipeline
-   **Storage**: Add `get_unarchived_intimations(con, limit)` and `mark_as_archived(con, id, url)` to `src/causaganha/v2/storage/queries.py`.
-   **Pipeline**: Create `src/causaganha/v2/pipeline/archive.py`.
    -   It should accept `ArchiveService` and `DocumentService` as dependencies (or create them).
    -   It should iterate over unarchived intimations, download PDF, upload to IA, and update DB.
    -   It needs to be async.

### 2. CLI Migration
-   **Dependencies**: The CLI currently instantiates V1 repositories (`IntimationRepository`, etc.). These should be replaced by V2 `get_connection()` and pipeline functions.
-   **Commands**:
    -   `collect`: Use `v2.pipeline.collect.collect_metadata_for_court`.
    -   `archive`: Use `v2.pipeline.archive.archive_documents`.
    -   `analyze`: Use `v2.pipeline.analyze.analyze_pending_decisions`.
    -   `score`: Use `v2.pipeline.score.calculate_ratings`.

### 3. Testing
-   **Unit**: Add tests for new Archive pipeline.
-   **E2E**: Update `tests/e2e/test_full_lifecycle.py` to mock the correct V2 components.
    -   Mock `v2.api.client.PJeAPIClient`.
    -   Mock `v2.pipeline.analyze.DecisionAnalyzer` (or the underlying LLM).
    -   Verify data in DuckDB using V2 storage queries or Ibis.

## Risks & Mitigation
-   **Data Compatibility**: Ensure V2 schema matches what V1 was writing, or if schema changes are handled. (V2 schema creation is already in `test_storage.py`, need to confirm `cli.py` uses it).
-   **Service Reusability**: `DocumentService` and `ArchiveService` are infrastructure components. They should be reusable. If they rely on V1 domain models, we might need adapters.
