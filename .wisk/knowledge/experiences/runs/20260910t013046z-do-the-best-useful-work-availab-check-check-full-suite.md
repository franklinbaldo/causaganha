---
type: "RunCheck"
id: "run-checks/20260910t013046z-do-the-best-useful-work-availab/check-full-suite"
run: "runs/20260910T013046Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check .; uv run ruff format --check .; uv run pytest -q; uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "All green: ruff check 'All checks passed!'; ruff format --check '408 files already formatted'; full pytest suite (all modules, not just tests/knowledge/) passed with 1 pre-existing skip and 0 failures; okf-parser check reports conformant:true, 0 diagnostics, 1129 concepts. Confirms the BacklogItem schema/test change is self-contained and the two regenerated files (domain_models.py, processoConsultar.gen.ts) match the current knowledge bundle exactly."
status: "pass"
evidence: "run-evidence/20260910t013046z-do-the-best-useful-work-availab/evidence-red-green-tests"
goal: "run-goals/20260910t013046z-do-the-best-useful-work-availab/goal-decouple-backlog-from-agentrun"
---

# RunCheck
