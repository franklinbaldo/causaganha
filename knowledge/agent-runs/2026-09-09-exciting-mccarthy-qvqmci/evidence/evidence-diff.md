---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-qvqmci-evidence-diff"
run_id: "2026-09-09-exciting-mccarthy-qvqmci"
goal_id: "2026-09-09-exciting-mccarthy-qvqmci-goal-stats-coverage-exclude-in-flight"
kind: "diff"
reference: "web/src/queries/stats_coverage.qmd, tests/test_render_queries.py"
summary: "git diff --stat: web/src/queries/stats_coverage.qmd (+33/-6), tests/test_render_queries.py (+79). stats_coverage.qmd's SQL gained a classified CTE (uploaded/raw_absent booleans, raw_absent using the same djen_raw IN ('404','400','no_publications') vocabulary as site_status.qmd) and a per-date 'unsettled' count (NOT uploaded AND NOT raw_absent); best_count/best_day/worst_count/worst_day now use FILTER (WHERE unsettled = 0) on top of MAX/MIN/ARG_MAX/ARG_MIN, while avg_coverage stays computed over the full window (see AgentDecision on scope). tests/test_render_queries.py gained one fixture (manifest_parquet_stats_coverage_with_in_flight_day: 3 tribunals x 3 days -- a fully-uploaded best day, a settled worst day with one genuine absent, and today with 2 still-pending tribunals) and one test asserting worst_day/worst_count/best_day/best_count all resolve against the settled data only."
---

# Evidência: diff

Mudança confinada a `stats_coverage.qmd` (nova classificação `uploaded`/`raw_absent`/`unsettled` e filtro no best/worst) e ao novo teste + fixture em `tests/test_render_queries.py`.
