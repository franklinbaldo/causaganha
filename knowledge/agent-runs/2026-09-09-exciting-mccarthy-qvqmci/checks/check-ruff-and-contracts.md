---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-qvqmci-check-ruff-and-contracts"
run_id: "2026-09-09-exciting-mccarthy-qvqmci"
goal_id: "2026-09-09-exciting-mccarthy-qvqmci-goal-stats-coverage-exclude-in-flight"
command: "uv run ruff check . && uv run ruff format --check . && uv run python scripts/render_queries.py --check"
result: "passed"
summary: "ruff check: All checks passed! ruff format --check: 403 files already formatted. render_queries.py --check: all 19 .qmd contracts (including the modified stats_coverage.qmd) validate OK against their synthetic schemas -- the new classified/daily CTEs and FILTER clauses don't reference any unknown column or view."
---

# Check: ruff + validação estática dos contratos .qmd

Ruff limpo (check e format) e `--check` estático confirma que `stats_coverage.qmd` modificado continua um contrato válido.
