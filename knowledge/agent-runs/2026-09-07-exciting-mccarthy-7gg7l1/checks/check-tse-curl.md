---
type: AgentCheck
id: "2026-09-07-exciting-mccarthy-7gg7l1-check-tse-curl"
run_id: "2026-09-07-exciting-mccarthy-7gg7l1"
goal_id: "2026-09-07-exciting-mccarthy-7gg7l1-goal-reconcile-backlog"
command: "curl -sS -o /dev/null -w 'HTTP:%{http_code}\\n' --max-time 15 https://cdn.tse.jus.br/estatistica/sead/"
result: "observed"
evidence_id: "2026-09-07-exciting-mccarthy-7gg7l1-evidence-tse-403"
summary: "HTTP:403. Confirms #985 (network_access) remains correctly blocked from this session's egress."
---

# Check: acesso de rede ao TSE
