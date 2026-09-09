---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-8kw55y-evidence-green-tests"
run_id: "2026-09-09-exciting-mccarthy-8kw55y"
goal_id: "2026-09-09-exciting-mccarthy-8kw55y-goal-lawyer-ratings-ia-fallback"
kind: "test_green"
reference: "tests/test_render_queries.py::test_register_lawyer_ratings_falls_back_to_ia_when_local_absent, ::test_register_ratings_history_falls_back_to_ia_when_local_absent, ::test_register_lawyer_ratings_prefers_local_over_ia"
summary: "uv run pytest tests/test_render_queries.py -k \"lawyer_ratings or ratings_history\" -v, after adding _LAWYER_RATINGS_IA_URL/_RATINGS_HISTORY_IA_URL constants and a shared _register_ratings_table(con, name, filename, ia_url) helper (local-file-exists check first, then _try_download_parquet fallback, mirroring _register_acordaos) that _register_lawyer_ratings/_register_ratings_history now delegate to: 3 passed, 44 deselected -- including the local-preference regression guard."
---

# GREEN: fallback IA implementado

Os 3 testes (2 antes RED + 1 preexistente de preferência local) passam após a correção.
