---
goal: "Fix CircuitBreaker's dead exponential-backoff branch on a failed half-open probe"
id: "run-goals/20260907t172906z-do-the-best-useful-work-availab/goal-fix-circuit-breaker-backoff"
kind: "task-advance"
rationale: "allow_request() eagerly flips HALF_OPEN->OPEN and resets _opened_at before the probe request runs, so record_failure()'s own state re-derivation (_state_locked()) always sees OPEN with ~0 elapsed time, never HALF_OPEN -- the 'reopen with doubled timeout' branch documented in the class docstring is dead code except in the near-impossible case where a request takes longer than recovery_timeout. In production this means archive.upload_zip's circuit breaker never escalates its retry cadence against a genuinely-still-down/WAF-throttled IA endpoint, contradicting CLAUDE.md's IA-reliability rules and the class's own documented contract."
run: "runs/20260907T172906Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "A new pytest-bdd scenario (tests/djen_backup/circuit_breaker.feature: 'Failed test request reopens the circuit with a doubled timeout') fails RED against the unmodified circuit_breaker.py (assert 1.0 == 2.0) and passes GREEN after adding an explicit _probing flag that record_failure() checks instead of re-deriving half-open from already-clobbered state; the existing 3 scenarios and the rest of the pytest suite stay green."
type: "RunGoal"
---

# RunGoal
