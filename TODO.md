# CausaGanha v2 - Implementation Todo

## Phase 1: Parallel Development (✅ Completed)

- [x] **Setup Environment**
    - [x] Create `src/causaganha/` directory structure
    - [x] Install dependencies (`pydantic-ai`, `ibis-framework[duckdb]`, `httpx`, `structlog`)
    - [x] Configure `ruff.toml` and `.pre-commit-config.yaml`
    - [x] Setup `pytest` configuration

- [x] **Implement PJe API Client (TDD)**
    - [x] Create `tests/unit/test_api_client.py`
    - [x] Implement `PJeAPIClient` in `src/causaganha/api/client.py`
    - [x] Implement pagination logic
    - [x] Implement error handling

- [x] **Implement Ibis Storage Layer (TDD)**
    - [x] Create `tests/unit/test_storage.py`
    - [x] Implement `get_connection` and schema initialization
    - [x] Implement `store_intimations` and other queries

- [x] **Implement Pydantic AI Analyzer (TDD)**
    - [x] Create `tests/unit/test_analyzer.py`
    - [x] Implement `DecisionAnalyzer` using Pydantic AI
    - [x] Define `DecisionAnalysis` model (with structured OAB fields)

- [x] **Implement Scoring Module (TDD)**
    - [x] Create `tests/unit/test_scoring.py`
    - [x] Implement `src/causaganha/scoring/openskill.py` (ported from V1)

- [x] **Implement Pipeline Orchestration (TDD)**
    - [x] Create `tests/integration/test_pipeline_collect.py`
    - [x] Implement `collect.py`
    - [x] Implement `analyze.py`
    - [x] Implement `score.py` (Lawyer Ratings)
    - [x] Create `tests/integration/test_pipeline_score.py`

## Phase 2: Integration & Validation (✅ Completed)

- [x] Validation scripts (`src/causaganha/validation/` and `scripts/validate_data_quality.py`)
- [x] Comparison with v1 data (`scripts/compare_v1_v2.py`)
- [x] Improve Test Coverage (CLI, DocumentService)

## Phase 2.5: Cloud Infrastructure Stabilization (✅ Completed)

- [x] **Fix Cloud Dependencies**
    - [x] Add `google-cloud-firestore`, `google-cloud-pubsub`, `google-cloud-tasks` to `pyproject.toml`.
    - [x] Fix `tests/cloud/test_cloud_pipeline.py` execution (ImportError/AttributeError).
- [x] **Test Cloud Functions**
    - [x] Create `tests/cloud/test_llm_worker.py` (Unit tests for `llm_worker` and `process_llm`).
    - [x] Fix missing imports and potential bugs in `src/causaganha/cloud/functions/llm.py`.
    - [x] Create `tests/cloud/test_ingest_worker.py` (Unit tests for `ingest_worker`).
    - [x] Achieve >80% coverage for `src/causaganha/cloud/`.
- [x] **Refactor Cloud Config**
    - [x] Use `pydantic-settings` or `src/causaganha/config.py` for cloud env vars instead of `os.getenv` scattered around.

## Phase 3: Multi-Tribunal Expansion (✅ Completed)

- [x] **Configuration for Multiple Courts**
    - [x] Update `config.py` to support a list of courts/API endpoints.
- [x] **Refactor Pipeline for Multi-Court**
    - [x] Update `collect.py` to iterate over configured courts.
    - [x] Update `archive.py` to organize files by court (e.g., `TJRO/YYYY/MM/...`).

## Phase 4: System Hardening (⚠️ Partial)
- [x] **End-to-End Testing**
    - [x] Create `tests/e2e/test_full_lifecycle.py`.
    - [ ] Update E2E test to verify V2 flow (currently verifies V1).
- [x] **Documentation**
    - [x] Update `README.md` with new architecture diagrams.
    - [x] Generate API docs with `mkdocs`.

## Phase 5: V2 Integration & Migration (🚧 In Progress)
- [ ] **Implement V2 Archive Pipeline**
    - [ ] Add archive queries to `src/causaganha/v2/storage/queries.py`
    - [ ] Create `src/causaganha/v2/pipeline/archive.py`
- [ ] **Migrate CLI to V2**
    - [ ] Update `src/causaganha/cli.py` to use V2 pipeline modules
    - [ ] Verify `collect` command
    - [ ] Verify `archive` command
    - [ ] Verify `analyze` command
    - [ ] Verify `score` command
- [ ] **Verify E2E**
    - [ ] Ensure `tests/e2e/test_full_lifecycle.py` passes with V2 components
