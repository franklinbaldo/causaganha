---
type: "RunCheck"
id: "run-checks/20260910t182322z-do-the-best-useful-work-availab/check-full-suite-and-lint"
run: "runs/20260910T182322Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check && uv run ruff format --check && uv run pytest tests/test_ia_practicality_probe.py -q && uv run pytest -q (full suite)"
result: "ruff check: All checks passed. ruff format --check: 2 files already formatted. tests/test_ia_practicality_probe.py: 2 passed (first-ever tests for this file). Full uv run pytest -q: entire suite green, zero failures."
status: "pass"
evidence: "run-evidence/20260910t182322z-do-the-best-useful-work-availab/evidence-red-green-remove-warnings"
goal: "run-goals/20260910t182322z-do-the-best-useful-work-availab/goal-decide-ia-probe-warnings"
---

# RunCheck
