---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-5pmmrp-evidence-diff-fix"
run_id: "2026-09-08-exciting-mccarthy-5pmmrp"
goal_id: "2026-09-08-exciting-mccarthy-5pmmrp-goal-fix-window-off-by-one"
kind: "diff"
reference: "git diff web/src/queries/stats_coverage.qmd web/src/queries/daily_uploads.qmd"
summary: "Two one-character-class fixes: stats_coverage.qmd line 15 `WHERE date >= CURRENT_DATE - INTERVAL 30 DAY` -> `WHERE date > CURRENT_DATE - INTERVAL 30 DAY`; daily_uploads.qmd line 17 `AND date >= CURRENT_DATE - INTERVAL 120 DAY` -> `AND date > CURRENT_DATE - INTERVAL 120 DAY`. No schema/contract/frontmatter change -- output shape (avg_coverage/best_count/best_day/worst_count/worst_day for stats_coverage; date/count rows for daily_uploads) is unchanged, only the set of dates included shrinks by exactly the boundary day in each case."
---

# Evidência de diff

Duas mudanças de um caractere: `>=` para `>` no filtro de data de `stats_coverage.qmd` e `daily_uploads.qmd`. Nenhuma mudança de schema/contrato.
