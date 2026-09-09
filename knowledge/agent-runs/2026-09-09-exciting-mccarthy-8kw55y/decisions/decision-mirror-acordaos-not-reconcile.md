---
type: AgentDecision
id: "2026-09-09-exciting-mccarthy-8kw55y-decision-mirror-acordaos-not-reconcile"
run_id: "2026-09-09-exciting-mccarthy-8kw55y"
goal_id: "2026-09-09-exciting-mccarthy-8kw55y-goal-lawyer-ratings-ia-fallback"
question: "Should _register_lawyer_ratings/_register_ratings_history's IA fallback mirror _register_acordaos's single _try_download_parquet(url, dest, label) call, or reconcile_processos.ensure_juris_parquets()/ensure_datajud_parquets()'s heavier multi-shard discovery-and-dedup pattern (used by the previous round's, pf1xhn, fix for _register_tjro_juris/_register_datajud_capa)?"
choice: "Mirror _register_acordaos's single-URL pattern. Delegating to a new reconcile_processos.ensure_ratings_parquets() analogous to ensure_juris_parquets() was considered and rejected as premature -- there is no existing multi-source discovery need for ratings, and it would require inventing IA item-discovery logic (via IA advanced search or a hardcoded item list) that doesn't exist today for this pipeline, purely to match a pattern that doesn't apply to a single fixed-URL artifact."
rationale: "lawyer_ratings/ratings_history are not produced or discovered by scripts/reconcile_processos.py at all -- they come from a separate pipeline (scripts/pipeline/export_ratings.py querying catalog/catalog.duckdb) that uploads directly to a single, fixed, known filename per table on the causaganha-catalog IA item (lawyer_ratings.parquet, ratings_history.parquet), with no multi-shard/multi-year discovery or dedup concern (there is exactly one row per (lawyer, date) already, no overlapping monthly IA items to merge). _register_acordaos faces the exact same shape of problem -- one canonical parquet, one fixed IA URL, download-if-local-absent -- and already solves it with a single _try_download_parquet call. Reusing reconcile_processos's heavier discovery machinery here would add indirection with no corresponding correctness benefit, and would wrongly imply these two views are reconciler-managed sources when they are not."
---

# Decisão: espelhar `_register_acordaos`, não `reconcile_processos`

`lawyer_ratings`/`ratings_history` têm URL IA fixa e única (sem múltiplos shards/anos a descobrir e deduplicar), então o padrão simples de `_register_acordaos` (`_try_download_parquet` direto) é o correto -- delegar a `reconcile_processos.py` adicionaria indireção sem ganho de correção.
