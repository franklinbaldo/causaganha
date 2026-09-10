---
type: "RunCheck"
id: "run-checks/20260910t132702z-do-the-best-useful-work-availab/check-verification"
run: "runs/20260910T132702Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q (full suite); uv run ruff check; uv run ruff format --check; uv run okf-parser check .wisk/knowledge and uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "Full pytest suite green (no failures/errors), ruff check clean, ruff format --check clean repo-wide. Both OKF bundles remain structurally conformant with zero diagnostics after this round's .wisk experience/goal/evidence writes."
status: "pass"
evidence: "run-evidence/20260910t132702z-do-the-best-useful-work-availab/evidence-red-green-diff"
goal: "run-goals/20260910t132702z-do-the-best-useful-work-availab/goal-annotate-llm-adr-citation"
---

# RunCheck
