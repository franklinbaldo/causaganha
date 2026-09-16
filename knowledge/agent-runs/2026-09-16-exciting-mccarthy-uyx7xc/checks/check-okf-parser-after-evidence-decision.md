---
type: AgentCheck
id: "2026-09-16-exciting-mccarthy-uyx7xc-check-okf-parser-after-evidence-decision"
run_id: "2026-09-16-exciting-mccarthy-uyx7xc"
goal_id: "2026-09-16-exciting-mccarthy-uyx7xc-goal-djen-sample-batch3"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "conformant: true, 0 diagnostics, concept_count=1777, markdown_count=1780 -- run after the second AgentDecision and the two AgentEvidence records for the HTML-markup finding and the batch3 ingestion outcome were added. Caught and fixed 3 schema mismatches from the first draft: AgentCheck's real field names are command/result/summary (not procedure/result with no goal_id), result must be one of passed/failed/observed, AgentGoal.status must be one of proposed/active/achieved/carried, and AgentEvidence.kind must be one of the fixed enum values (used 'other' and 'runtime')."
---

# Check: okf-parser apos evidencias e segunda decisao

Confirma bundle conformante apos adicionar as duas `AgentEvidence` e a
segunda `AgentDecision` desta rodada. Corrigiu 3 desvios de schema do
rascunho inicial (nomes de campo de `AgentCheck`, enum de `result`, enum
de `status` do goal, enum de `kind` da evidencia).
