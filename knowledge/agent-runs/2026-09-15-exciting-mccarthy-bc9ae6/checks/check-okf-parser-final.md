---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-bc9ae6-check-okf-parser-final"
run_id: "2026-09-15-exciting-mccarthy-bc9ae6"
goal_id: "2026-09-15-exciting-mccarthy-bc9ae6-goal-scale-segmenter-reviews"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "conformant=true, 1661 concepts, 0 diagnostics após run.md finalizado e decision-resultado-single-anchor-fix.md corrigido para os nomes de campo corretos do schema AgentDecision (question/choice)."
---

# Check: okf-parser final

`uv run okf-parser check knowledge --relational-schema okf.schema.sql` retornou `conformant: true`, `diagnostics: []`, `concept_count: 1661`. Confirma que o bundle inteiro (incluindo os 2 novos `ReviewRecord`s/`AnnotationRecord`s de dados e o relatório `AgentRun` completo desta rodada) permanece estruturalmente válido.
