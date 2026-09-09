---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-ez5wkn-check-ruff-and-contracts"
run_id: "2026-09-09-exciting-mccarthy-ez5wkn"
goal_id: "2026-09-09-exciting-mccarthy-ez5wkn-goal-datajud-join-key-normalization"
command: "uv run ruff check . && uv run ruff format --check . && uv run python scripts/render_queries.py --check"
result: "passed"
evidence_id: "2026-09-09-exciting-mccarthy-ez5wkn-evidence-full-suites-green"
summary: "ruff check: All checks passed! ruff format --check: 403 files already formatted. render_queries.py --check: all 19 .qmd contracts validate OK, including processos_multi_fonte.qmd (the sole consumer of the modified processos_unificados view)."
---

# Check: ruff + validação estática dos contratos .qmd

Ruff limpo e `--check` estático confirma que `processos_multi_fonte.qmd` continua um contrato válido após a mudança em `_DATAJUD_AGG_SQL`.
