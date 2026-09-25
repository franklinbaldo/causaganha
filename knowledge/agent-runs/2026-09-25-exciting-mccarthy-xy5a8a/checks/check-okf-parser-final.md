---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-xy5a8a-check-okf-parser-final"
run_id: "2026-09-25-exciting-mccarthy-xy5a8a"
goal_id: "2026-09-25-exciting-mccarthy-xy5a8a-goal-processo-consultar-evidence-marker"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: "2026-09-25-exciting-mccarthy-xy5a8a-evidence-green-processo-consultar-marker"
summary: "Apos finalizar run.md e corrigir os nomes de campo de AgentGoal/AgentEvidence/AgentCheck/AgentDecision para bater com knowledge/okf.schema.sql (a primeira tentativa usava campos livres como motivation/description/procedure/decision, rejeitados pelo schema relacional), o check final reporta conformant=true, 0 diagnostics, sobre os 2362 concepts do bundle inteiro (13 novos desta rodada: 1 AgentRun, 4 AgentReading, 1 AgentGoal, 1 AgentDecision, 2 AgentEvidence, 3 AgentCheck)."
---

# Check: okf-parser final

Rodado ao final da rodada, após o `run.md` estar completo e os campos
dos novos concepts corrigidos para bater com o schema relacional
(`knowledge/okf.schema.sql`) — 0 diagnósticos, bundle inteiro
conformante.
