---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-orr2e3-check-deploy-mcp-workflow-runs"
run_id: "2026-09-25-exciting-mccarthy-orr2e3"
goal_id: "2026-09-25-exciting-mccarthy-orr2e3-goal-950-reopen"
command: "mcp__github__actions_list(method=list_workflow_runs, owner=franklinbaldo, repo=causaganha, resource_id='deploy-mcp.yml')"
result: "passed"
evidence_id: "2026-09-25-exciting-mccarthy-orr2e3-evidence-deploy-workflow-zero-runs"
summary: "`total_count: 0` -- confirma que o rollout remoto de #950 nunca foi executado."
---

# Check: contagem de execuções de `deploy-mcp.yml`
