---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-8esdwh-check-okf-parser-baseline"
run_id: "2026-09-09-exciting-mccarthy-8esdwh"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: "2026-09-09-exciting-mccarthy-8esdwh-evidence-pr-1364-closed"
summary: "Ran three times during setup: (1) with the scaffold's empty id fields still blank -- conformant (empty strings not yet FK-referenced anywhere); (2) after filling run.md's id/reading ids -- surfaced OKF022 FK errors because the four readings' run_id pointed at an AgentRun id not yet materialized, and because goal_id: \"\" on the housekeeping decision/evidence was resolved as a literal (non-null) FK value with no matching AgentGoal; (3) after fixing run.md's id and omitting goal_id entirely (rather than empty string) on the two housekeeping instances -- conformant, 0 diagnostics, 991 concepts."
---

# Check: okf-parser baseline

Confirmado conformante após corrigir o `id` do `run.md` e omitir `goal_id` (em vez de string vazia) nas instâncias de housekeeping sem goal associado.
