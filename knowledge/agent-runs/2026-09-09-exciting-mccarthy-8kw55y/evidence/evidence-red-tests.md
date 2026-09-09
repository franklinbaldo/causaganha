---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-8kw55y-evidence-red-tests"
run_id: "2026-09-09-exciting-mccarthy-8kw55y"
goal_id: "2026-09-09-exciting-mccarthy-8kw55y-goal-lawyer-ratings-ia-fallback"
kind: "test_red"
reference: "tests/test_render_queries.py::test_register_lawyer_ratings_falls_back_to_ia_when_local_absent, ::test_register_ratings_history_falls_back_to_ia_when_local_absent, ::test_register_lawyer_ratings_prefers_local_over_ia"
summary: "uv run pytest tests/test_render_queries.py -k \"lawyer_ratings or ratings_history\" -v, before touching scripts/render_queries.py: 2 failed, 1 passed, 44 deselected. The two IA-fallback tests (monkeypatch DEV_RATINGS_DIR to an empty dir and _try_download_parquet to a fake returning a prepared local parquet) failed with `assert False is True` -- confirming _register_lawyer_ratings/_register_ratings_history never called _try_download_parquet at all and simply returned False, exactly the live bug the goal describes. The third test (prefers local over IA) passed unmodified, as expected -- the pre-fix code already preferred local files when present; it is a regression guard for after the fix, not a RED case."
---

# RED: lawyer_ratings/ratings_history IA fallback ausente

`uv run pytest tests/test_render_queries.py -k "lawyer_ratings or ratings_history" -v` antes da correção: 2 falhas confirmando exatamente o bug (funções retornam `False` mesmo com fallback IA simulado disponível).
