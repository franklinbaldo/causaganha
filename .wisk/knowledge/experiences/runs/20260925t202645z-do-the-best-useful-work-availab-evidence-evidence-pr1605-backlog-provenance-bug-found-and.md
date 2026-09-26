---
type: "RunEvidence"
id: "run-evidence/20260925t202645z-do-the-best-useful-work-availab/evidence-pr1605-backlog-provenance-bug-found-and"
run: "runs/20260925T202645Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "First merge attempt set knowledge/backlog/issue-1050.md's last_verified_run_id to a fabricated 'wisk:20260925T202645Z-...' reference. Ran uv run pytest -q on the branch: FAILED tests/knowledge/test_backlog.py::test_every_backlog_item_last_verified_run_id_resolves_to_a_real_round -- the referenced Wisk LoopRun record only exists on this session's own branch (claude/exciting-mccarthy-80kc8l), not on PR #1605's branch, so it does not resolve there. Fixed by pointing last_verified_run_id/last_verified_at back at the already-valid, already-committed round 2026-09-24-exciting-mccarthy-e3tk18 / 2026-09-24T18:40:00Z (present in knowledge/agent-runs/ on both branches after the merge). Re-ran uv run pytest -q tests/knowledge/test_backlog.py -> 7 passed, then the full suite -> green."
summary: "Caught and fixed a real cross-branch provenance-reference bug before it reached CI, via a genuine RED->GREEN local test cycle -- not just plausible-looking edits."
goal: "run-goals/20260925t202645z-do-the-best-useful-work-availab/goal-resume-pr-1605"
---

# RunEvidence
