---
type: "RunGoal"
id: "run-goals/20260907t192551z-do-the-best-useful-work-availab/goal-fix-circuit-breaker-is-open"
run: "runs/20260907T192551Z-do-the-best-useful-work-available-in-this-reposi"
kind: "task-advance"
goal: "Fix CircuitBreaker.is_open (src/djen_backup/circuit_breaker.py) to reflect time-based HALF_OPEN recovery instead of staying permanently OPEN"
rationale: "is_open compares against raw self._state (== CircuitState.OPEN) instead of the dynamic self.state property that promotes OPEN to HALF_OPEN once recovery_timeout has elapsed. Investigated as a deferred lead from the prior round's outcome (20260907T184502Z): the only caller, src/causaganha/pipeline/ia_s3.py:227 (upload_to_ia, used by consolidate/cli.py and scripts/pipeline/consolidate.py with a long-lived breaker reused across many uploads in one run), never calls allow_request()/record_success(), so once the breaker trips OPEN it can never self-heal for the rest of that run -- every subsequent upload is silently skipped forever, even long after IA recovers. The other lead from that same outcome (archive.py:264's 'except Exception') was investigated and ruled out: ruff's BLE001 intentionally exempts handlers that call a *.exception(...) logger, which log.exception(...) satisfies, so it is correct as written, not a lint gap."
success_signal: "tests/djen_backup/test_circuit_breaker.py gains a scenario proving that after threshold failures + recovery_timeout elapsed, is_open becomes False (matching the already-tested state==HALF_OPEN promotion), written RED first (fails against the current raw self._state comparison), then GREEN after the one-line fix; full pytest -q, ruff check and ruff format --check stay green; a PR is opened and driven to a green, mergeable state."
status: "active"
---

# RunGoal
