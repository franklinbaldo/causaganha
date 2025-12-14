# CausaGanha v2 - Implementation Todo

## Phase 1: Parallel Development

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

## Phase 2: Integration & Validation

- [x] Validation scripts
- [ ] Comparison with v1 data
