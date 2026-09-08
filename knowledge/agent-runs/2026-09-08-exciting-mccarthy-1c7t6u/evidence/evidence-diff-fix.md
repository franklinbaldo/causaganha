---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-1c7t6u-evidence-diff-fix"
run_id: "2026-09-08-exciting-mccarthy-1c7t6u"
goal_id: "2026-09-08-exciting-mccarthy-1c7t6u-goal-consolidation-threshold"
kind: "diff"
reference: "git diff web/src/queries/consolidation_status.qmd tests/test_render_queries.py"
summary: "web/src/queries/consolidation_status.qmd: replaced the unused uploaded_dates CTE with a tribunal_universe CTE computing COUNT(DISTINCT tribunal) FROM manifest, dropped the outer WHERE ia_status='uploaded' filter from daily_counts (now grouping over the whole manifest), and rewrote the three COUNT(*) FILTER clauses to compare against (SELECT total_tribunals FROM tribunal_universe) instead of the literal 90/90. tests/test_render_queries.py: new CONSOLIDATION_STATUS_QMD constant, manifest_parquet_small_tribunal_universe fixture, and test_consolidation_status_counts_a_date_with_every_tracked_tribunal_as_fully_uploaded."
---

# Evidencia: diff do fix

Ver `web/src/queries/consolidation_status.qmd` e `tests/test_render_queries.py` no diff da branch `claude/exciting-mccarthy-1c7t6u`.
