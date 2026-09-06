---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-usm2ot-check-okf-parser"
run_id: "2026-09-06-exciting-mccarthy-usm2ot"
goal_id: "2026-09-06-exciting-mccarthy-usm2ot-goal-backlog-cache"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-usm2ot-evidence-green-backlog-test"
summary: "conformant: true, 0 diagnostics, after adding BacklogItem to okf.schema.sql and populating knowledge/backlog/ with 17 issue files + index.md. Concept count grew from 427 (start of round) to 451 (17 BacklogItem + this round's own AgentRun-family concepts). All PK/FK metadata for the new type (issue_number PK, last_verified_run_id FK -> AgentRun) resolves cleanly."
---

# Check: okf-parser conformante com BacklogItem

`okf-parser check` segue `conformant: true` com 0 diagnósticos depois de acrescentar o type `BacklogItem` e os 17 arquivos de backlog.
