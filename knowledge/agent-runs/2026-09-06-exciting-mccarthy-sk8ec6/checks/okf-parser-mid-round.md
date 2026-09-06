---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-sk8ec6-check-okf-parser-mid-round"
run_id: "2026-09-06-exciting-mccarthy-sk8ec6"
goal_id: "2026-09-06-exciting-mccarthy-sk8ec6-goal-fix-1193-dataset-availability"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-sk8ec6-evidence-component-diff"
summary: "Run before this round's own records existed: conformant=true, 0 diagnostics, concept_count=349. Confirms the bundle was healthy at round start, establishing the baseline this round's new AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck records are added on top of."
---

# Check: okf-parser (início da rodada)

`conformant: true`, 0 diagnósticos, 349 conceitos — baseline antes dos registros desta rodada.
