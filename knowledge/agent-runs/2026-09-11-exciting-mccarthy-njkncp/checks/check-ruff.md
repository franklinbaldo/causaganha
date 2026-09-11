---
type: AgentCheck
id: "2026-09-11-exciting-mccarthy-njkncp-check-ruff"
run_id: "2026-09-11-exciting-mccarthy-njkncp"
goal_id: "2026-09-11-exciting-mccarthy-njkncp-goal-cobertura-malformed-report"
command: "uv run ruff check . && uv run ruff format --check ."
result: "passed"
summary: "ruff check: All checks passed! ruff format --check: 422 files already formatted. Clean repo-wide after the fix (service.py + test_service.py changes included)."
---

# Check: ruff limpo

`uv run ruff check .` e `uv run ruff format --check .` limpos em todo o repositório, incluindo as mudanças desta rodada.
