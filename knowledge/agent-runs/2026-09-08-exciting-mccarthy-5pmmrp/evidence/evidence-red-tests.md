---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-5pmmrp-evidence-red-tests"
run_id: "2026-09-08-exciting-mccarthy-5pmmrp"
goal_id: "2026-09-08-exciting-mccarthy-5pmmrp-goal-fix-window-off-by-one"
kind: "test_red"
reference: "uv run pytest -q tests/test_render_queries.py -k \"30_days_excludes or 120_days_excludes\" (before the fix)"
summary: "Before the fix, both new tests failed exactly as predicted. stats_coverage: manifest rigged with an outlier collected-count of 3 on the boundary date (today-30) and 1 on every other date in the 30-day window; assertion `payload[\"best_count\"] == 1` failed with `assert 3 == 1` -- the boundary day's outlier leaked into best_count/avg_coverage because the >= filter admitted 31 dates. daily_uploads: manifest with exactly two rows (today-120 and today-119); assertion `boundary_iso not in dates` failed with `assert '2026-05-11' not in ['2026-05-11', '2026-05-12']` -- the >= filter admitted the 121st boundary day. Result: 2 failed, both AssertionErrors on the exact lines above."
---

# Evidência RED

Rodei os dois testes novos contra o SQL original (`>=`) e ambos falharam pelo motivo esperado: o dia-limite (hoje-30 / hoje-120) entrava no cálculo. `best_count` veio 3 em vez de 1 (o outlier do dia-limite vazou pro melhor dia); `daily_uploads` incluiu a data-limite na lista de datas retornadas.
