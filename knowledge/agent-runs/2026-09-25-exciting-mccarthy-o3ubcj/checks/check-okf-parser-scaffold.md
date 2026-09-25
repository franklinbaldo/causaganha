---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-o3ubcj-check-okf-parser-scaffold"
run_id: "2026-09-25-exciting-mccarthy-o3ubcj"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "failed"
summary: "Rodado logo após criar readings/goal/decisions/evidence/checks mas antes de preencher run.md com um `id` real: 12 diagnósticos OKF022 (foreign key sem AgentRun correspondente), um por arquivo -- esperado, pois o scaffold ainda tinha `id: \"\"`. Usado para confirmar que o parser resolve corretamente todas as referências run_id/goal_id/evidence_id antes de qualquer trabalho de produto começar, e para orientar o próximo passo (preencher run.md)."
---

# Check: okf-parser check (scaffold ainda incompleto -- orienta o próximo passo)
