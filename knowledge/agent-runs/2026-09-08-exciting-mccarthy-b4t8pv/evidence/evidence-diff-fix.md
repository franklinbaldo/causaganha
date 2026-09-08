---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-b4t8pv-evidence-diff-fix"
run_id: "2026-09-08-exciting-mccarthy-b4t8pv"
goal_id: "2026-09-08-exciting-mccarthy-b4t8pv-goal-confirmed-pending-undercount"
kind: "diff"
reference: "git diff web/src/queries/totals.qmd web/src/queries/tribunal_coverage.qmd"
summary: "Two one-line SQL changes: totals.qmd:15 and tribunal_coverage.qmd:15 change `WHERE djen_status = 'available' AND ia_status != 'uploaded'` to `WHERE djen_status IN ('available', 'confirmed') AND ia_status != 'uploaded'` in the `pending` FILTER clause. No other lines touched in either file."
---

# Evidencia: diff do fix

Duas mudancas de uma linha cada, mesmo padrao em `totals.qmd` e `tribunal_coverage.qmd`.
