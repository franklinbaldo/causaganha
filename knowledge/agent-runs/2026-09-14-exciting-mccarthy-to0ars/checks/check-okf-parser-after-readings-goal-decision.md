---
type: AgentCheck
id: "2026-09-14-exciting-mccarthy-to0ars-check-okf-parser-after-readings-goal-decision"
run_id: "2026-09-14-exciting-mccarthy-to0ars"
goal_id: "2026-09-14-exciting-mccarthy-to0ars-goal-verify-values-bucket"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: null
summary: "Ran after writing the 4 AgentReading files, the goal, and the AgentDecision. First attempt failed: OKF022, AgentDecision.goal_id='' had no matching AgentGoal (empty string is not NULL for the FK check). Fixed by setting goal_id: null in the decision's frontmatter (this decision is about process/schedule policy, not tied to the domain goal). Re-ran: conformant=true, 0 diagnostics, concept_count=1310, markdown_count=1313."
---

# Check: okf-parser após leituras, goal e decisão

Primeira tentativa falhou (`OKF022`, `goal_id: ""` não é NULL para a FK). Corrigido para `goal_id: null` no `AgentDecision` (decisão sobre política de agendamento, não presa ao goal de domínio). Segunda execução: `conformant: true`, 0 diagnósticos.
