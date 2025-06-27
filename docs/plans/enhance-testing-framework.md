# Enhance Testing Framework

## Problem Statement
- **What problem does this solve?**
  The current test suite has low coverage (around 16% mentioned in `fix-database-integration-issues.md`) and a significant number of failing tests (20/77). This indicates potential gaps in testing, making it difficult to ensure code quality, prevent regressions, and confidently refactor or add new features.
- **Why is this important?**
  A robust testing framework is crucial for maintaining a stable and reliable application, especially with ongoing development and planned expansions like multi-tribunal support. Higher test coverage and more comprehensive tests reduce the risk of introducing bugs, improve developer confidence, and facilitate easier debugging.
- **Current limitations**
  - Low unit test coverage for many modules.
  - Lack of comprehensive integration tests for pipeline stages.
  - Absence of end-to-end tests verifying the entire workflow.
  - Existing failing tests hinder CI/CD effectiveness.

## Proposed Solution
- **High-level approach**
  Systematically improve the testing framework by fixing existing failing tests, increasing unit test coverage, adding integration tests for key components and pipeline stages, and introducing end-to-end tests for critical user workflows.
- **Technical architecture**
  1.  **Test Pyramid Strategy**: Adhere to the testing pyramid concept: a large base of unit tests, a smaller layer of integration tests, and a minimal set of end-to-end tests.
  2.  **Unit Tests**: Ensure each module and function has isolated tests. Focus on `src/` modules.
  3.  **Integration Tests**:
      - Test interactions between components (e.g., CLI and DatabaseManager, Extractor and LLM service).
      - Test individual pipeline stages (Queue, Archive, Analyze, Score) with mocked dependencies where appropriate.
  4.  **End-to-End (E2E) Tests**: Simulate user workflows using the CLI to process a small, controlled set of test documents through the entire pipeline. These tests will use real services (like a test IA item or a local mock IA server if feasible, and potentially a rate-limited LLM for a single document).
  5.  **Test Data Management**: Create a dedicated set of test data (sample PDFs, CSVs) that are version-controlled and used consistently across tests.
  6.  **Mocking Strategy**: Utilize `pytest-mock` and `unittest.mock` effectively to isolate components and simulate external services (IA, LLM APIs, tribunal websites).
  7.  **CI Integration**: Ensure all tests (unit, integration, E2E) run in the CI pipeline (`test.yml`). Failing tests must fail the build.
  8.  **Coverage Reporting**: Configure `coverage.py` to accurately report test coverage and set targets for improvement.

- **Implementation steps**
  1.  **Phase 1: Stabilize Existing Tests & Basic Coverage (Weeks 1-2)**
      - Analyze and fix all currently failing 20 tests.
      - Improve unit test coverage for critical modules like `src/database.py`, `src/config.py`, `src/utils.py` to at least 70%.
      - Set up accurate coverage reporting in CI.
  2.  **Phase 2: Integration Tests for Core Components (Weeks 3-4)**
      - Develop integration tests for `DatabaseManager` interacting with a test database.
      - Write integration tests for `GeminiExtractor` (mocking the Gemini API).
      - Write integration tests for `ia_database_sync.py` (potentially using a mock IA environment or a dedicated test item on IA).
      - Write integration tests for the main CLI commands (`queue`, `archive`, `analyze`, `score`, `pipeline`) focusing on their interaction with the database and file system.
  3.  **Phase 3: End-to-End Tests (Weeks 5-6)**
      - Design 2-3 E2E test scenarios covering the main pipeline workflow.
      - Scenario 1: Successful processing of a single valid PDF from queue to score.
      - Scenario 2: Handling of a problematic PDF (e.g., invalid format, LLM extraction failure).
      - Implement these E2E tests using `subprocess` to invoke the CLI or by directly calling Typer app commands.
      - Create necessary test data (PDFs, expected outputs).
  4.  **Phase 4: Increase Coverage & Refine (Ongoing)**
      - Incrementally increase unit and integration test coverage for remaining modules (`async_diario_pipeline.py`, tribunal-specific adapters, etc.).
      - Refine mocking strategies and test data management.
      - Set a target overall coverage of >75%.

## Success Criteria
- **Test Stability**: All (100%) existing and new tests pass consistently in local and CI environments.
- **Coverage Increase**: Overall test coverage increased to at least 75%. Critical modules achieve >80% coverage.
- **Integration Test Suite**: A suite of integration tests covers interactions between key components and individual pipeline stages.
- **E2E Test Suite**: At least two E2E tests successfully validate the main pipeline workflow.
- **CI Reliability**: CI pipeline reliably runs all tests and fails builds if any test fails.
- **Improved Code Quality**: Reduced bug introduction rate in new features or refactoring efforts.
- **Developer Confidence**: Developers feel more confident making changes due to a reliable test safety net.

## Implementation Plan (High-Level for this document)
1.  **Stabilize & Core Unit Tests**: Fix failing tests. Add unit tests for `database.py`, `config.py`, `utils.py`.
2.  **Component Integration Tests**: Tests for `DatabaseManager`, `GeminiExtractor`, `ia_database_sync.py`.
3.  **CLI Integration Tests**: Tests for `causaganha queue`, `archive`, `analyze`, `score`, `pipeline` commands.
4.  **E2E Workflow Tests**: Implement 2-3 full pipeline E2E tests.
5.  **Broaden Coverage**: Incrementally add tests for other modules like `async_diario_pipeline.py`, `ia_discovery.py`, and tribunal adapters.

## Risks & Mitigations
- **Risk 1: Flaky E2E Tests**: E2E tests interacting with external services can be slow and unreliable.
  - *Mitigation*:
    - Minimize reliance on external services in E2E tests where possible (e.g., use local mocks for IA if feasible, or a dedicated test IA item).
    - Design E2E tests to be resilient to minor network issues (e.g., implement retries for certain operations).
    - Run E2E tests less frequently if they are very slow (e.g., nightly builds instead of every commit).
- **Risk 2: Complex Mocking**: Mocking complex interactions (e.g., async operations, external APIs) can be challenging.
  - *Mitigation*:
    - Use established mocking libraries (`pytest-mock`, `aresponses` for aiohttp).
    - Develop reusable mocking utilities.
    - Focus on testing the contract with the external service rather than its internal logic.
- **Risk 3: Time Investment**: Achieving high test coverage can be time-consuming.
  - *Mitigation*:
    - Prioritize testing critical paths and complex logic first.
    - Encourage writing tests as part of the development process for new features (TDD/BDD principles).
    - Distribute test writing effort across the development team.
- **Risk 4: Test Data Management**: Managing and maintaining test data can become cumbersome.
  - *Mitigation*:
    - Store test data in the repository (for small datasets).
    - Use fixtures to generate test data programmatically where possible.
    - Clearly document the purpose and structure of test data.

## Dependencies
- `pytest`: Core testing framework.
- `pytest-mock`: For mocking.
- `coverage.py`: For test coverage measurement.
- Potentially `aresponses` or `aiohttp.pytest_plugin` for testing async HTTP requests if not already used.
- `ia-test-data` (hypothetical): A separate, small repository or IA item for storing larger test assets if needed.
