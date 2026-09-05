---
type: AgentCheck
id: "2026-09-05-eager-wozniak-5akx2o-check-okf-conformant"
run_id: "2026-09-05-eager-wozniak-5akx2o"
goal_id: "2026-09-05-eager-wozniak-5akx2o-goal-enforce-completeness"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: "2026-09-05-eager-wozniak-5akx2o-evidence-enforcement-gap"
summary: "conformant: true, concept_count: 18, 0 diagnostics — the whole knowledge bundle, including this round's full typed report tree, is structurally valid (PK/FK level) even though CHECK-level completeness needed the new project-owned checker to be caught at all."
---

# Check: okf-parser check final do bundle
