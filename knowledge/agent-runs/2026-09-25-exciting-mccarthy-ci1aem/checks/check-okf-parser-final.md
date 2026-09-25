---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-ci1aem-check-okf-parser-final"
run_id: "2026-09-25-exciting-mccarthy-ci1aem"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "conformant=true, 0 diagnosticos, 2233 conceitos -- rodado apos preencher completed_at/decision_ids/evidence_ids/check_ids/result_summary/next_move neste run.md (a rodada anterior do mesmo comando, com o relatorio ainda em rascunho, apontava 5 erros OKF022 de foreign key run_id nao resolvida)."
---

# Verificacao final: okf-parser check

Confirma que o bundle `knowledge/` inteiro, incluindo o `AgentRun` desta
propria rodada e todos os seus componentes (`AgentReading`, `AgentGoal`,
`AgentDecision`, `AgentEvidence`, `AgentCheck`), continua conformante ao
`okf.schema.sql` apos o relatorio ser preenchido por completo.
