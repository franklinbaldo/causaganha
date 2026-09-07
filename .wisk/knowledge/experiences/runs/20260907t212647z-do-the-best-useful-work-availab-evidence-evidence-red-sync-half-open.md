---
type: "RunEvidence"
id: "run-evidence/20260907t212647z-do-the-best-useful-work-availab/evidence-red-sync-half-open"
run: "runs/20260907T212647Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/djen_backup/circuit_breaker.feature (new scenario); tests/djen_backup/test_circuit_breaker.py (new step when_sync_probe_fails + scenario binding)"
summary: "TRIBUNAL=tjro uv run pytest tests/djen_backup/test_circuit_breaker.py -q against unmodified src/djen_backup/circuit_breaker.py: the new scenario fails with AssertionError -- circuit_breaker.state is CircuitState.HALF_OPEN, expected CircuitState.OPEN, after a sync-style probe (is_open check followed directly by record_failure(), no allow_request()) failed. Confirms the defect precisely: a failed half-open probe via the sync-only path never reopens the circuit."
goal: "goal-fix-circuit-breaker-sync-half-open-reopen"
---

# RunEvidence
