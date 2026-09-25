---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-0lqpmv-check-mcp-deployment-tests"
run_id: "2026-09-25-exciting-mccarthy-0lqpmv"
goal_id: "2026-09-25-exciting-mccarthy-0lqpmv-goal-supply-chain-lock-nonroot"
command: "uv run pytest -q tests/deployment/test_mcp_deployment.py"
result: "passed"
evidence_id: "2026-09-25-exciting-mccarthy-0lqpmv-evidence-green-tests"
summary: "8/8 verde: 3 testes pré-existentes (entrypoint/limites, ausência de credenciais no artefato, GIT_SHA no cloudbuild) + 5 novos desta rodada (uv.lock commitado, Dockerfile pina digest, Dockerfile usa uv sync --frozen a partir do lock, Dockerfile roda como usuário não-root antes do CMD, CI setup action usa --frozen). Rodado antes (RED, ver evidence-red-tests) e depois (GREEN) da implementação."
---

# Check: suíte de deployment do MCP
