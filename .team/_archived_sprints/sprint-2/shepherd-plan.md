# Plan: Shepherd - Sprint 2

**Persona:** Shepherd 🧑‍🌾
**Sprint:** 2
**Created:** 2026-01-26
**Priority:** High

## Objectives
<<<<<<< HEAD
<<<<<<< HEAD
My mission is to ensure the "Structure & Polish" sprint yields a robust, verifiable system. I will focus on testing the new configuration system, the decomposed runner, and critical database components.

- [ ] **Config Security Verification:** Create behavioral tests to verify that the new Pydantic configuration correctly masks secrets and handles environment variable overrides.
- [ ] **Runner Integration Tests:** Verify that the decomposed `runner.py` components interact correctly, mocking external API calls with `respx`.
- [ ] **Database Coverage Boost:** Increase test coverage for `DuckDBManager` and `EloStore` to >80%, focusing on error handling and edge cases.
- [ ] **Sprint Feedback:** Provide feedback on all Sprint 2 plans (Completed).

## Dependencies
- **Artisan:** I rely on the new `config` and `runner` implementations to be available for testing.
- **Sentinel:** I will align my config security tests with their requirements.

## Context
As the code structure changes significantly in Sprint 2, existing tests may break or become irrelevant. My role is to adapt the test suite to the new structure and ensure we don't lose coverage during the transition.

## Expected Deliverables
1. `tests/behavior/test_config_security.py`
2. `tests/behavior/test_runner_integration.py`
3. Increased coverage for `src/egregora/database/` (>80% for target files).
4. `shepherd-feedback.md`
=======
My mission is to build a safety net for the major refactoring ("Structure & Polish") occurring this sprint. I aim to raise behavioral test coverage and ensure no regressions in critical pipelines.

- [ ] **Coverage Milestone:** Increase global test coverage to **60%** (currently ~58-59%).
- [ ] **Verify ETL Extraction:** Create behavioral tests for the new `src/egregora/orchestration/pipelines/etl/` module (supporting Simplifier).
- [ ] **Verify Runner De-composition:** Create behavioral tests for the refactored `runner.py` components (supporting Artisan).
- [ ] **Scaffolding Stability:** Ensure the `scaffolding.py` module (Project Init) is fully covered (completed in Sprint 1/Early Sprint 2).

## Dependencies
- **Simplifier:** I need the interface definitions for the new ETL module to write tests.
- **Artisan:** I need the new `runner` component structure to design appropriate test suites.

## Context
Sprint 2 involves breaking down the `write.py` monolith and the `runner.py` complex. These are the highest-risk changes in the codebase. If we break the pipeline, the system stops working. My role is to verify *behavior* so they can change *implementation* safely.

## Expected Deliverables
1.  **Test Suite:** New tests in `tests/unit/orchestration/pipelines/etl/`.
2.  **Test Suite:** New tests in `tests/unit/orchestration/runner/`.
3.  **Config:** Updated `pyproject.toml` with `fail_under = 60`.
4.  **CI:** Green CI pipeline throughout the refactor.
>>>>>>> origin/pr/2874

## Risks and Mitigations
| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
<<<<<<< HEAD
| Refactor breaks many tests | High | High | I will prioritize fixing "behavioral" tests first, as they describe *what* the system does. Implementation tests can be deleted if they verify obsolete internal logic. |
=======
| Tests tightly coupled to old implementation | High | Medium | Focus strictly on Input/Output verification (Behavioral Tests), ignoring internal state where possible. |
| Coverage drops during refactor | Medium | High | enforce coverage checks on every PR. If code moves, tests must move (or be rewritten). |

## Proposed Collaborations
- **With Simplifier:** Pair programming on TDD for ETL extraction.
- **With Artisan:** Reviewing `runner` refactor PRs for testability.
>>>>>>> origin/pr/2874
=======
**Created on:** 2026-01-26
**Priority:** High

## Objectives

Describe the main objectives for this sprint:

- [ ] Improve coverage for `src/egregora/agents/writer.py` to >60%.
- [ ] Improve coverage for `src/egregora/agents/enricher.py` to >50%.
- [ ] Stabilize existing benchmarks and add new ones for writer performance.

## Dependencies

List dependencies on work from other personas:

- **Refactor:** Coordination on any writer refactoring to avoid test churn.

## Context

Explain the context and reasoning behind this plan:

During Sprint 1, I focused on fixing broken tests and improving coverage for `formatting.py`. The core agents (`writer` and `enricher`) still have significant coverage gaps which poses a risk for regression.

## Expected Deliverables

1. Behavioral test suite for `writer.py`.
2. Behavioral test suite for `enricher.py`.
3. Updated coverage thresholds.

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| Tests becoming flaky due to mocks | Medium | High | Use `respx` and careful mocking strategies. |
| Code churn in agents | High | Medium | Communicate with Refactor/Typeguard personas. |

## Proposed Collaborations

- **With Refactor:** Ensure refactoring preserves behavior verified by new tests.

## Additional Notes

Focus remains on "Behavioral" testing - verifying outputs and side effects.
>>>>>>> origin/pr/2834
