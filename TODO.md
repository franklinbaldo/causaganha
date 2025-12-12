# CausaGanha v2 - Implementation Todo

## Phase 1: Parallel Development

- [x] **Setup Environment**
    - [x] Create `v2/` directory structure
    - [x] Install dependencies (`pydantic-ai`, `ibis-framework[duckdb]`, `httpx`, `structlog`)
    - [x] Configure `ruff.toml` and `.pre-commit-config.yaml`
    - [x] Setup `pytest` configuration

- [x] **Implement PJe API Client (TDD)**
    - [x] Create `tests/v2/unit/test_api_client.py` with initial failing test
    - [x] Implement `PJeAPIClient` in `src/causaganha/v2/api/client.py`
    - [x] Implement pagination logic
    - [x] Implement error handling

- [ ] **Implement Ibis Storage Layer (TDD)**
    - [ ] Create `tests/v2/unit/test_storage.py`
    - [ ] Implement `get_connection` and schema initialization
    - [ ] Implement `store_intimations` and other queries

- [ ] **Implement Pydantic AI Analyzer (TDD)**
    - [ ] Create `tests/v2/unit/test_analyzer.py`
    - [ ] Implement `DecisionAnalyzer` using Pydantic AI
    - [ ] Define `DecisionAnalysis` model

- [ ] **Implement Pipeline Orchestration (TDD)**
    - [ ] Create `tests/v2/integration/test_pipeline.py`
    - [ ] Implement `collect.py`
    - [ ] Implement `analyze.py`

## Phase 2: Integration & Validation

- [ ] Validation scripts
- [ ] Comparison with v1 data
