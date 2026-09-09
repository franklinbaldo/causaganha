---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-8kw55y-evidence-diff-fix"
run_id: "2026-09-09-exciting-mccarthy-8kw55y"
goal_id: "2026-09-09-exciting-mccarthy-8kw55y-goal-lawyer-ratings-ia-fallback"
kind: "diff"
reference: "scripts/render_queries.py, tests/test_render_queries.py, web/src/queries/README.md"
summary: "git diff --stat scripts/render_queries.py tests/test_render_queries.py web/src/queries/README.md: scripts/render_queries.py | 30 ++++++++++++--- ; tests/test_render_queries.py | 87 +++++++++++++++++++++++++++++++++++++++++++ ; web/src/queries/README.md | 4 +-. scripts/render_queries.py: added _LAWYER_RATINGS_IA_URL/_RATINGS_HISTORY_IA_URL constants (https://archive.org/download/causaganha-catalog/{lawyer_ratings,ratings_history}.parquet, matching scripts/pipeline/export_ratings.py's upload_to_ia(item_id='causaganha-catalog', ...) target) and a new _register_ratings_table() helper that _register_lawyer_ratings/_register_ratings_history now call instead of _register_local_parquet directly -- local-file-exists check first, IA download fallback via the existing _try_download_parquet second. tests/test_render_queries.py: added the 3 tests described in evidence-red-tests/evidence-green-tests. web/src/queries/README.md: updated the lawyer_ratings/ratings_history Data Sources table rows to say '(ratings pipeline, local or IA)', matching how the acordaos/tjro_juris rows already describe their own local-or-IA fallback."
---

# Diff da correção

`scripts/render_queries.py` ganha fallback IA para `lawyer_ratings`/`ratings_history`, espelhando `_register_acordaos`; testes e README atualizados junto.
