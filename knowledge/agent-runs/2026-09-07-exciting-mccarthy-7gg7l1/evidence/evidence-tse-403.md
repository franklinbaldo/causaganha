---
type: AgentEvidence
id: "2026-09-07-exciting-mccarthy-7gg7l1-evidence-tse-403"
run_id: "2026-09-07-exciting-mccarthy-7gg7l1"
goal_id: "2026-09-07-exciting-mccarthy-7gg7l1-goal-reconcile-backlog"
kind: "runtime"
reference: "curl -sS -o /dev/null -w 'HTTP:%{http_code}\\n' --max-time 15 https://cdn.tse.jus.br/estatistica/sead/ (this session, 2026-09-07)"
summary: "HTTP:403 — reproduces the same Akamai edge rejection prior rounds (589obm) recorded for issue #985, from this session's own network egress. The merged acquisition/inspection/profiling code in src/tse_processual/ needs no further implementation; the block remains purely network-level."
---

# Evidência: TSE ainda retorna 403

`curl` a `https://cdn.tse.jus.br/estatistica/sead/` retornou `HTTP:403`.
