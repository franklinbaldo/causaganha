---
type: AgentCheck
id: "2026-09-16-exciting-mccarthy-mg2tp1-check-okf-parser-after-evidence-decision"
run_id: "2026-09-16-exciting-mccarthy-mg2tp1"
goal_id: "2026-09-16-exciting-mccarthy-mg2tp1-goal-djen-sample-batch4"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "conformant: true, 0 diagnostics, concept_count=1792, markdown_count=1795, reserved_count=3 -- run after the batch4 evidence and the NBSP-patch decision were written."
---

# Check: okf-parser apos evidencia e segunda decisao

Rodado apos criar a `AgentEvidence` `evidence-batch4-ingested` e a
segunda `AgentDecision` `decision-patch-nbsp-instead-of-redo`. Bundle
conformante, sem diagnosticos.
