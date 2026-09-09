---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-pf1xhn-evidence-diff-fix"
run_id: "2026-09-09-exciting-mccarthy-pf1xhn"
goal_id: "2026-09-09-exciting-mccarthy-pf1xhn-goal-juris-datajud-ia-fallback"
kind: "diff"
reference: "git diff scripts/render_queries.py (73 lines); git diff tests/test_render_queries.py (+111 lines, 3 new tests)"
summary: "scripts/render_queries.py: added `from scripts import reconcile_processos` import; rewrote _register_datajud_capa to call reconcile_processos.ensure_datajud_parquets() instead of globbing data/datajud/ directly; rewrote _register_tjro_juris to call reconcile_processos.ensure_juris_parquets() instead of globbing data/tjro_juris/ directly, adding an id_documento-partitioned dedup query (ROW_NUMBER() OVER (PARTITION BY id_documento ORDER BY extraido_em DESC NULLS LAST)) when ensure_juris_parquets() reports needs_dedup=True, mirroring reconcile_processos._register_juris's own dedup. Both functions' bool contract (True = view registered, False = _ensure_view's synthetic fallback) is unchanged. tests/test_render_queries.py: added test_register_datajud_capa_falls_back_to_ia_when_local_absent, test_register_tjro_juris_falls_back_to_ia_when_local_absent, test_register_tjro_juris_dedups_overlapping_ia_shards, each monkeypatching reconcile_processos.ensure_datajud_parquets/ensure_juris_parquets to simulate the IA-fallback case with no real network access."
---

# Evidência de diff

`scripts/render_queries.py`: `_register_datajud_capa`/`_register_tjro_juris` agora delegam a `reconcile_processos.ensure_datajud_parquets()`/`ensure_juris_parquets()` em vez de só varrer um diretório local que nunca é populado em CI, preservando o contrato booleano existente e portando a deduplicação por `id_documento` para o caso de shards mensais sobrepostos.
