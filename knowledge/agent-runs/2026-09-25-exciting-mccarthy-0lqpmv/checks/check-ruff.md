---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-0lqpmv-check-ruff"
run_id: "2026-09-25-exciting-mccarthy-0lqpmv"
goal_id: "2026-09-25-exciting-mccarthy-0lqpmv-goal-supply-chain-lock-nonroot"
command: "uv run ruff check && uv run ruff format --check"
result: "passed"
evidence_id: "2026-09-25-exciting-mccarthy-0lqpmv-evidence-green-tests"
summary: "ruff check: All checks passed. ruff format --check: 1 arquivo (tests/deployment/test_mcp_deployment.py) precisou de reformat (ajuste de aspas), aplicado via `uv run ruff format`; segunda rodada de --check ficou limpa (461 arquivos já formatados)."
---

# Check: ruff check + format
