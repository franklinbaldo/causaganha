# Plan: Shepherd - Sprint 3

**Persona:** Shepherd 🧑‍🌾
**Sprint:** 3
**Created:** 2026-01-26
<<<<<<< HEAD
<<<<<<< HEAD
**Priority:** High

## Objectives
My mission is to verify the "Symbiote Shift" features, specifically the Universal Context Layer API and real-time capabilities.

- [ ] **API Contract Testing:** Create comprehensive tests for the new Universal Context Layer API (RFC 026) using `respx` and schema validation.
- [ ] **Real-time Performance Benchmarks:** Add benchmarks for the new "Fetch-then-Compute" windowing logic to ensure it meets performance goals (O(1) slicing).
- [ ] **API Security Verification:** Verify authentication mechanisms and localhost binding for the new API.
- [ ] **Documentation Testing:** Verify that code examples in the new documentation are executable and correct.

## Dependencies
- **Visionary/Simplifier:** I need the API implementation (RFC 026) to be ready for testing.
- **Lore:** I will use the "Oral History" context to understand the expected behavior of legacy systems being replaced.

## Context
Sprint 3 introduces a new API surface area. This is the critical moment to establish a "Testing Contract" for external consumers (plugins, symbiotes).

## Expected Deliverables
1. `tests/api/test_context_layer.py`
2. `tests/performance/test_realtime_fetching.py`
3. `tests/security/test_api_auth.py`
=======
**Priority:** Medium

## Objectives
My mission is to support the "Symbiote Shift" and the move toward real-time processing by introducing performance regression testing and integration verification.

- [ ] **Latency Regression Framework:** Establish a baseline for message processing time and add automated checks (supporting Bolt).
- [ ] **Context Layer Verification:** Create integration tests for the new Universal Context Layer API (supporting Visionary).
- [ ] **Async Testing:** Implement `pytest-asyncio` patterns to verify the new async ingestion layer without race conditions.
- [ ] **Coverage Milestone:** Target **65%** global test coverage.

## Dependencies
- **Bolt:** I need the new Async Architecture and Latency Budget definitions.
- **Visionary:** I need the API spec for the Context Layer.

## Context
Sprint 3 shifts focus from Structure to Performance and Integration. The risks change from "breaking logic" to "introducing latency" or "race conditions". My testing strategy must adapt to measure time and concurrency, not just correctness.

## Expected Deliverables
1.  **Performance Tests:** `tests/perf/` suite using `pytest-benchmark` or custom latency assertions.
2.  **Async Tests:** Concurrency-safe tests for the new ingestion layer.
3.  **Integration Tests:** End-to-end verification of the Context API.
>>>>>>> origin/pr/2874

## Risks and Mitigations
| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
<<<<<<< HEAD
| API spec changes frequently | Medium | Medium | I will write tests against the *interface* (OpenAPI spec/Pydantic models) to detect drift early. |
=======
| Flaky Async Tests | High | Medium | Use `pytest-asyncio` strict mode and avoid `time.sleep()`. Use deterministic event loop control where possible. |
| Performance Noise in CI | High | Low | Set generous thresholds for CI, but strict thresholds for local benchmarks. |

## Proposed Collaborations
- **With Bolt:** Define "Latency Budget" and how to measure it reliably.
- **With Visionary:** Validate the Context Layer API contract.
>>>>>>> origin/pr/2874
=======
**Created on:** 2026-01-26
**Priority:** Medium

## Objectives

- [ ] Achieve >65% overall project coverage.
- [ ] Implement property-based testing (Hypothesis) for critical data schemas.
- [ ] Audit and improve slow-running tests.

## Dependencies

- **Builder:** Stable schemas for property-based testing.

## Context

After solidifying coverage for core agents in Sprint 2, Sprint 3 will focus on depth (property testing) and efficiency (test speed).

## Expected Deliverables

1. Hypothesis test suite for Documents and Schemas.
2. Performance report on test suite.
3. Optimized test configuration.

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| Property tests finding too many edge cases | Low | Medium | Prioritize fixing critical bugs first. |

## Proposed Collaborations

- **With Builder:** Verify schema constraints robustness.

## Additional Notes

N/A
>>>>>>> origin/pr/2834
