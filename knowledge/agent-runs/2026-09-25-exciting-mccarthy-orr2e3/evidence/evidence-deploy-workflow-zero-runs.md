---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-orr2e3-evidence-deploy-workflow-zero-runs"
run_id: "2026-09-25-exciting-mccarthy-orr2e3"
goal_id: "2026-09-25-exciting-mccarthy-orr2e3-goal-950-reopen"
kind: "other"
reference: "mcp__github__actions_list(method=list_workflow_runs, resource_id='deploy-mcp.yml')"
summary: "`list_workflow_runs` para `deploy-mcp.yml` retornou `{\"total_count\":0,\"workflow_runs\":[]}` -- o workflow de rollout do MCP remoto (que produziria `mcp-rollout-proof.json` e a URL pública exigida pelo critério de conclusão da issue #950) nunca foi executado, nem manualmente nem por qualquer trigger, em toda a história do repositório. Confirma que o rollout operacional descrito nos comentários de #950 (2026-09-01 a 2026-09-07) nunca aconteceu, apesar de a issue ter sido fechada em 2026-09-25T10:15:17Z."
---

# Evidência: `deploy-mcp.yml` nunca rodou

`list_workflow_runs` confirma `total_count: 0` para o workflow de
rollout do MCP remoto -- base factual para reabrir `#950`.
