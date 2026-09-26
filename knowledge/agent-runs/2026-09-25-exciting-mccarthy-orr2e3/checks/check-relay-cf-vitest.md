---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-orr2e3-check-relay-cf-vitest"
run_id: "2026-09-25-exciting-mccarthy-orr2e3"
goal_id: "2026-09-25-exciting-mccarthy-orr2e3-goal-tm02-stale-doc"
command: "cd deployment/relay-cf && npm ci --silent && npx vitest run"
result: "passed"
evidence_id: "2026-09-25-exciting-mccarthy-orr2e3-evidence-tm02-diff"
summary: "18/18 testes verdes, incluindo 'strips Authorization and Cookie before forwarding upstream' e 'strips Set-Cookie from the upstream response' -- confirma ao vivo (não apenas por leitura do código) que o comportamento que TM-02 chamava de pendente já está implementado e coberto por teste antes de editar a documentação."
---

# Check: suíte Vitest do CF relay
