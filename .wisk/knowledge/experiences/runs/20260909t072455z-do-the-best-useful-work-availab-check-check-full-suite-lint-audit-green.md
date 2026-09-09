---
type: "RunCheck"
id: "run-checks/20260909t072455z-do-the-best-useful-work-availab/check-full-suite-lint-audit-green"
run: "runs/20260909T072455Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q; uv run ruff check; uv run ruff format --check; uv run python scripts/segmenter_semantic_audit.py"
result: "pytest: 526 passed (full suite, incl. 2 new tests: the RED/GREEN regression test and the real-store regression guard). ruff check: all checks passed. ruff format --check: all files formatted. segmenter_semantic_audit.py against data/segmenter: 1 finding (the documented false positive), down from 14 before this change."
status: "pass"
evidence: "run-evidence/20260909t072455z-do-the-best-useful-work-availab/evidence-repair-run-observed"
goal: "run-goals/20260909t072455z-do-the-best-useful-work-availab/goal-repair-segmenter-audit-1050"
---

# RunCheck
