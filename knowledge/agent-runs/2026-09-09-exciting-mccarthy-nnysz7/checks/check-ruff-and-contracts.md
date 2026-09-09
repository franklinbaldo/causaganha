---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-nnysz7-check-ruff-and-contracts"
run_id: "2026-09-09-exciting-mccarthy-nnysz7"
goal_id: "2026-09-09-exciting-mccarthy-nnysz7-goal-totals-coverage-pct-null-not-nan"
command: "uv run ruff check tests/test_render_queries.py scripts/render_queries.py && uv run ruff format --check tests/test_render_queries.py; uv run python -c \"from scripts import render_queries as rq; print(rq.check_queries())\""
result: "passed"
evidence_id: "2026-09-09-exciting-mccarthy-nnysz7-evidence-diff"
summary: "ruff check limpo, ruff format --check limpo (após um ruff format que ajustou uma linha longa na nova asserção), e check_queries() confirma os 19 contratos .qmd, incluindo totals.qmd, todos OK."
---

# Check: ruff e validação estática de contratos

`ruff check` limpo, `ruff format --check` limpo, e `check_queries()` (equivalente ao `--check` de `render_queries.py`) confirma os 19 contratos `.qmd`, incluindo `totals.qmd`, todos `OK`.
