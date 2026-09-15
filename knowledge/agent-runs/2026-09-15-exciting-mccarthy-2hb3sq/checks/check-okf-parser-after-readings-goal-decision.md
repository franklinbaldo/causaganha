---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-2hb3sq-check-okf-parser-after-readings-goal-decision"
run_id: "2026-09-15-exciting-mccarthy-2hb3sq"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "failed"
evidence_id: "2026-09-15-exciting-mccarthy-2hb3sq-evidence-adjudication-decisions"
summary: "OKF022 (foreign key sem match) em todos os AgentReading/AgentGoal/AgentDecision criados nesta rodada, todos apontando para o mesmo AgentRun.id ('2026-09-15-exciting-mccarthy-2hb3sq') que ainda não existia em run.md (scaffold com id vazio). Corrigido preenchendo run.md; reconfirmado passed em check-segmenter-suite/check-governance-status subsequentes e na checagem final."
---

# Check: okf-parser após leituras, goal e decisão iniciais

Rodado logo após criar as 4 leituras, o goal e a decisão iniciais, antes
de preencher `run.md` -- exatamente o comportamento esperado pelo próprio
scaffold ("use as lacunas apontadas pelo contrato para conduzir a própria
rodada"). Todas as falhas eram a mesma causa raiz (FK para um
`AgentRun.id` ainda vazio), não problemas distintos.
