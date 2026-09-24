---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-mjd1vm-check-okf-parser-final"
run_id: "2026-09-24-exciting-mccarthy-mjd1vm"
goal_id: "2026-09-24-exciting-mccarthy-mjd1vm-goal-land-stalled-prs"
procedure: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "pass"
evidence_id: "2026-09-24-exciting-mccarthy-mjd1vm-evidence-pr-1597-merged"
---

# Check: okf-parser conformante ao final da rodada

`uv run okf-parser check knowledge --relational-schema okf.schema.sql`
retornou `conformant: true`, `diagnostics: []` apos o relatorio desta
rodada estar completo (`completed_at`/`result_summary`/`next_move`
preenchidos), confirmando que o bundle OKF permanece valido antes do
push final deste `run.md`.
