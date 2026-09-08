---
type: "RunEvidence"
id: "run-evidence/20260908t042628z-do-the-best-useful-work-availab/evidence-red-then-green-drain-403"
run: "runs/20260908T042628Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/djen_backup/test_drain.py::test_drain_one_swallows_rate_limited"
summary: "RED: added test_drain_one_swallows_rate_limited mocking get_caderno_url to raise DJENRateLimitedError; it failed with the exception propagating out of _drain_one (pytest traceback: drain.py:98 -> DJENRateLimitedError uncaught). GREEN: added 'except DJENRateLimitedError' clause to _drain_one (src/djen_backup/drain.py) logging drain_skip_rate_limited and returning without marking absent or re-raising; the new test and the full 8-test tests/djen_backup/test_drain.py file pass."
goal: "run-goals/20260908t042628z-do-the-best-useful-work-availab/goal-fix-drain-403"
---

# RunEvidence
