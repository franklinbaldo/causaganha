---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-034xwb-check-okf-parser-after-readings-goal-decision"
run_id: "2026-09-24-exciting-mccarthy-034xwb"
goal_id: "2026-09-24-exciting-mccarthy-034xwb-goal-batch27-corpus-growth"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "pass"
evidence_id: null
summary: "Rodado apos escrever as 4 AgentReading, o AgentGoal e o AgentDecision desta rodada. Primeira tentativa falhou com OKF022 (AgentCheck.evidence_id='' nao casa com nenhum AgentEvidence -- string vazia nao e NULL para a checagem de FK, mesmo padrao ja documentado em rodadas anteriores como to0ars). Corrigido trocando evidence_id: \"\" por evidence_id: null no check baseline. Re-executado: conformant=true, 0 diagnosticos, concept_count=2108, markdown_count=2111."
---

# Check: okf-parser apos leituras, goal e decisao

Confirma que o bundle segue conformante apos a montagem inicial do
relatorio desta rodada (leituras + goal + decisao de continuidade).
Pego ao vivo um erro real de FK (string vazia vs `null`) igual ao ja
documentado por rodadas anteriores -- corrigido no proprio check
baseline.
