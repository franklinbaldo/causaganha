---
type: "RunEvidence"
id: "run-evidence/20260907t172906z-do-the-best-useful-work-availab/evidence-red-green-circuit-breaker"
run: "runs/20260907T172906Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/djen_backup/test_circuit_breaker.py::test_half_open_failure_doubles_timeout, tests/djen_backup/circuit_breaker.feature"
summary: "RED before the fix: assert circuit_breaker._recovery_timeout == recovery_timeout_before_probe * 2 failed with 'assert 1.0 == (1.0 * 2)' -- record_failure() re-derived half-open via _state_locked(), which always saw OPEN (already clobbered by allow_request()) with ~0 elapsed time, so the doubling branch never ran. GREEN after adding an explicit _probing flag (set in allow_request()'s HALF_OPEN branch, cleared in record_success()/record_failure()) that record_failure() checks directly instead of re-deriving from already-mutated state: all 4 circuit_breaker.feature scenarios pass, and TRIBUNAL=tjro uv run pytest -q is green across the full suite."
goal: "run-goals/20260907t172906z-do-the-best-useful-work-availab/goal-fix-circuit-breaker-backoff"
---

# RunEvidence
