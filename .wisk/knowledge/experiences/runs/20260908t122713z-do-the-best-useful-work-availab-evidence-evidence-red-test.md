---
type: "RunEvidence"
id: "run-evidence/20260908t122713z-do-the-best-useful-work-availab/evidence-red-test"
run: "runs/20260908T122713Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/test_absent_consistency_shared.py"
summary: "uv run pytest tests/test_absent_consistency_shared.py -q -> 2 failed, 6 passed. RED as expected: SyncManifest._normalize_event is not yet the shared normalize_absent, and render_manifest_parquet has no ABSENT_SELF_CONSISTENCY_SENTINEL constant yet. The parametrized SQL-vs-Python cross-consistency case already passes (both implementations already agree on values today, per PR #1323) -- this test's job is to keep them agreeing after the refactor, not to prove they currently disagree."
goal: "run-goals/20260908t122713z-do-the-best-useful-work-availab/goal-extract-shared-absent-consistency"
---

# RunEvidence
