---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-5crg57-check-okf-parser-after-merge"
run_id: "2026-09-15-exciting-mccarthy-5crg57"
goal_id: "2026-09-15-exciting-mccarthy-5crg57-goal-first-real-review-record"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: "2026-09-15-exciting-mccarthy-5crg57-evidence-pr-merged"
summary: "conformant: true, diagnostics: [], concept_count: 1443. Rodado após preencher completed_at/result_state=merged/result_summary/next_move do run.md e registrar as evidências de PR aberta/mesclada."
---

# Check: okf-parser contra o bundle knowledge, após o merge

Rodado como último passo da rodada, sobre o branch reiniciado a partir de `origin/main` (que já inclui o squash commit da PR #1505), antes de commitar o fechamento do relatório.
