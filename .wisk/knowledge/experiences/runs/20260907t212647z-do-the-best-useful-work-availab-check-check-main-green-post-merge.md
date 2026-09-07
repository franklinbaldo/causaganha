---
type: "RunCheck"
id: "run-checks/20260907t212647z-do-the-best-useful-work-availab/check-main-green-post-merge"
run: "runs/20260907T212647Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "git log --oneline -1; TRIBUNAL=tjro uv run pytest -q; uv run ruff check; uv run ruff format --check"
result: "HEAD is 553963e (the squash-merged PR #1291 commit). Full pytest -q suite: all tests pass (1 skipped, consistent with prior same-day baselines, zero failures). ruff check: All checks passed. ruff format --check: 389 files already formatted, clean. Confirms merging PR #1291 did not regress main."
status: "pass"
evidence: "evidence-pr-1291-merged"
goal: "goal-merge-pr-1291"
---

# RunCheck
