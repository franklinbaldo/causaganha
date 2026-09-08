---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-5pmmrp-evidence-green-tests"
run_id: "2026-09-08-exciting-mccarthy-5pmmrp"
goal_id: "2026-09-08-exciting-mccarthy-5pmmrp-goal-fix-window-off-by-one"
kind: "test_green"
reference: "uv run pytest -q tests/test_render_queries.py (after the fix)"
summary: "After changing `date >= CURRENT_DATE - INTERVAL N DAY` to `date > CURRENT_DATE - INTERVAL N DAY` in both stats_coverage.qmd and daily_uploads.qmd, the full tests/test_render_queries.py file (43 tests, including the 2 new ones and every pre-existing test in the file) passed with zero failures. The new stats_coverage test now sees best_count=1/worst_count=1/avg_coverage=1.0 (the boundary day's outlier of 3 excluded) and neither best_day nor worst_day equals the boundary date. The new daily_uploads test now sees exactly 1 row, and the boundary date is absent from the returned dates."
---

# Evidência GREEN

Após trocar `>=` por `>` em `stats_coverage.qmd` e `daily_uploads.qmd`, todo o arquivo `tests/test_render_queries.py` (43 testes) passou, incluindo os 2 novos e todos os pré-existentes -- sem regressão.
