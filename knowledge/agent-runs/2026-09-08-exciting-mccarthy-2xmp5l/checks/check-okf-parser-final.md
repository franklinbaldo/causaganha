---
type: AgentCheck
id: "2026-09-08-exciting-mccarthy-2xmp5l-check-okf-parser-final"
run_id: "2026-09-08-exciting-mccarthy-2xmp5l"
goal_id: "2026-09-08-exciting-mccarthy-2xmp5l-goal-delete-tribunal-calendar"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql && TRIBUNAL=tjro uv run pytest -q && uv run ruff check && uv run ruff format --check"
result: "passed"
summary: "okf-parser: conformant=true, 0 diagnostics, concept_count=724, markdown_count=727 — run after this round's run.md reached its finished state (completed_at, primary_goal_id, result_summary, next_move all filled, all evidence/check ids linked). ruff check: all checks passed. ruff format --check: 390 files already formatted (no Python files touched this round)."
---

# Check: okf-parser final

Rodado após finalizar `run.md` desta rodada. Conformante, 0 diagnósticos. `ruff check`/`ruff format --check` limpos (nenhum arquivo Python tocado nesta rodada).
