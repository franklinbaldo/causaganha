---
type: "RunCheck"
id: "run-checks/20260910t184124z-do-the-best-useful-work-availab/check-full-suite-and-lint"
run: "runs/20260910T184124Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check && uv run ruff format --check && uv run pytest tests/test_bootstrap_training_corpus.py -q && uv run pytest -q (full suite)"
result: "ruff check: All checks passed. ruff format --check: all files formatted (one auto-reformat applied to the new test file, then re-verified clean). tests/test_bootstrap_training_corpus.py: 2 passed (first-ever tests for this file). Full uv run pytest -q: entire suite green, zero failures."
status: "pass"
evidence: "run-evidence/20260910t184124z-do-the-best-useful-work-availab/evidence-red-green-stable-id"
goal: "run-goals/20260910t184124z-do-the-best-useful-work-availab/goal-fix-nondeterministic-id"
---

# RunCheck
