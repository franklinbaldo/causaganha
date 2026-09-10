---
type: "RunCheck"
id: "run-checks/20260910t042601z-do-the-best-useful-work-availab/check-full-suite-and-ruff"
run: "runs/20260910T042601Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q (full repo suite); uv run ruff check; uv run ruff format --check"
result: "Full repo suite green (no failures); ruff check reports 'All checks passed!'; ruff format --check reports all files already formatted (411 files)."
status: "pass"
evidence: "evidence-green-and-suite"
goal: "goal-fix-download-fail-fast"
---

# RunCheck
