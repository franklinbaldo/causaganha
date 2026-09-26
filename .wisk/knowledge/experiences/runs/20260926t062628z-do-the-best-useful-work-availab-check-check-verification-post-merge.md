---
type: "RunCheck"
id: "run-checks/20260926t062628z-do-the-best-useful-work-availab/check-verification-post-merge"
run: "runs/20260926T062628Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check; uv run ruff format --check; uv run okf-parser check knowledge --relational-schema okf.schema.sql; uv run python scripts/segmenter_governance_status.py; uv run pytest -q tests/segmenter_dataset (against local branch fast-forwarded to origin/main at bb8072d, the PR #1670 merge commit)"
result: "ruff check: all checks passed. ruff format --check: 462 files already formatted. okf-parser: conformant, 0 diagnostics (2565 markdown files after this round's own knowledge/backlog/issue-1051.md edit). segmenter_governance_status.py live output: document_count=197, annotation_count=260, review_count=37, val_count=30 (ceiling), test_count=7 (of 30 floor), meets_rfc_0012_split_floor=false -- matches PR #1670's own stated result exactly. pytest -q tests/segmenter_dataset: 438 passed (72+72+72+72+72+42+... =438 across 6 batches), exit code 0, zero failures -- first attempt hit a 280s local timeout (background task btjvaabb7, exit 143, not a test failure) before finishing; the same suite already passed 14/14 on GitHub CI (tests (tjro) job) against this exact commit before merge, so the timeout was a local time-budget issue, re-run with a 550s timeout completed clean."
status: "pass"
evidence: "runs/20260926T062628Z-do-the-best-useful-work-available-in-this-reposi"
goal: "run-goals/20260926t062628z-do-the-best-useful-work-availab/goal-shepherd-pr-1670"
---

# RunCheck
