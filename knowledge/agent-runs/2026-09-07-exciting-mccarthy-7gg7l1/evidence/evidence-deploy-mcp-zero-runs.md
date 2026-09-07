---
type: AgentEvidence
id: "2026-09-07-exciting-mccarthy-7gg7l1-evidence-deploy-mcp-zero-runs"
run_id: "2026-09-07-exciting-mccarthy-7gg7l1"
goal_id: "2026-09-07-exciting-mccarthy-7gg7l1-goal-reconcile-backlog"
kind: "ci"
reference: "mcp__github__actions_list(method=list_workflow_runs, owner=franklinbaldo, repo=causaganha, resource_id='deploy-mcp.yml')"
summary: "{\"total_count\":0,\"workflow_runs\":[]} — the 'Deploy MCP HTTP' workflow (.github/workflows/deploy-mcp.yml, a workflow_dispatch job requiring project_id/region/workload_identity_provider/service_account/artifact_repository/service_name/smoke_cnj inputs only a human can supply) has never been triggered in this repository's history. Confirms #950/#951's infra_decision block is a real, unexecuted rollout, not stale text describing a decision the owner already made elsewhere."
---

# Evidência: `deploy-mcp.yml` nunca foi executado

`list_workflow_runs` para `deploy-mcp.yml` retorna `total_count: 0`.
