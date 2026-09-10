---
type: "RunCheck"
id: "run-checks/20260910t112808z-do-the-best-useful-work-availab/check-verification"
run: "runs/20260910T112808Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q (full suite); uv run ruff check scripts/generate_homepage_widgets.py tests/test_generate_homepage_widgets.py; uv run ruff format --check scripts/generate_homepage_widgets.py tests/test_generate_homepage_widgets.py"
result: "Full pytest suite: all tests passed (1 pre-existing unrelated skip), exit code 0. ruff check: All checks passed. ruff format --check: 2 files already formatted."
status: "pass"
evidence: "run-evidence/20260910t112808z-do-the-best-useful-work-availab/evidence-red-green-homepage-widgets"
goal: "run-goals/20260910t112808z-do-the-best-useful-work-availab/goal-audit-scripts-long-tail"
---

# RunCheck
