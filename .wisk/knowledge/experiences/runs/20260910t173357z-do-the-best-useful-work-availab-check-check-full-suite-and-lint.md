---
type: "RunCheck"
id: "run-checks/20260910t173357z-do-the-best-useful-work-availab/check-full-suite-and-lint"
run: "runs/20260910T173357Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check && uv run ruff format --check && uv run pytest tests/test_evaluate_regex_segmenter.py -q && uv run pytest -q (full suite)"
result: "ruff check: All checks passed. ruff format --check: 2 files already formatted. tests/test_evaluate_regex_segmenter.py: 2 passed. Full uv run pytest -q: entire suite green, zero failures."
status: "pass"
evidence: "run-evidence/20260910t173357z-do-the-best-useful-work-availab/evidence-red-green-skipped-counter"
goal: "run-goals/20260910t173357z-do-the-best-useful-work-availab/goal-fix-skipped-counter"
---

# RunCheck
