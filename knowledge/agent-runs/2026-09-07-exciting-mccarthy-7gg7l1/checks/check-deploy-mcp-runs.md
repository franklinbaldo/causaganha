---
type: AgentCheck
id: "2026-09-07-exciting-mccarthy-7gg7l1-check-deploy-mcp-runs"
run_id: "2026-09-07-exciting-mccarthy-7gg7l1"
goal_id: "2026-09-07-exciting-mccarthy-7gg7l1-goal-reconcile-backlog"
command: "mcp__github__actions_list(method=list_workflow_runs, owner=franklinbaldo, repo=causaganha, resource_id='deploy-mcp.yml')"
result: "observed"
evidence_id: "2026-09-07-exciting-mccarthy-7gg7l1-evidence-deploy-mcp-zero-runs"
summary: "total_count=0. Confirms #950/#951 (infra_decision) remain correctly blocked — no rollout has ever executed."
---

# Check: histórico de execuções de `deploy-mcp.yml`
