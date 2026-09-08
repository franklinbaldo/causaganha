---
goal: "Make _drain_one (src/djen_backup/drain.py) swallow DJENRateLimitedError (HTTP 403 CloudFront/WAF block) the same way it already swallows DJENNotFoundError and httpx transport errors, instead of letting it propagate and permanently kill that drain worker task."
id: "run-goals/20260908t042628z-do-the-best-useful-work-availab/goal-fix-drain-403"
kind: "task-advance"
rationale: "get_caderno_url raises DJENRateLimitedError on HTTP 403 (djen.py:85-87), matching CLAUDE.md's 'never treat 403 as absent, it is transient' rule. _drain_one's except clauses catch DJENNotFoundError and (httpx.HTTPError, httpx.RequestError) but DJENRateLimitedError is a bare Exception subclass, not an httpx error, so it is never caught. It propagates out of _drain_one, then out of _drain_worker's while-True loop (which also has no matching except), permanently ending that asyncio task for the rest of the drain run. Under a real CloudFront rate-limit burst -- exactly the scenario the exception exists to handle -- each 403 removes one worker from the pool, degrading throughput when the system is already being throttled. engine.py and probe.py both already catch DJENRateLimitedError explicitly; drain.py is the one writer path that omits it."
run: "runs/20260908T042628Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "A new test (test_drain_one_swallows_rate_limited in tests/djen_backup/test_drain.py) mocks get_caderno_url to raise DJENRateLimitedError and asserts _drain_one returns normally (no exception propagates) with writer.count==0 and writer.absent_count==0 (403 is not absence). This test fails (RED) against the current code and passes (GREEN) after adding an except DJENRateLimitedError clause to _drain_one. Full pytest suite stays green; ruff check and ruff format --check stay clean. A PR is opened and driven to a green, mergeable state."
type: "RunGoal"
---

# RunGoal
