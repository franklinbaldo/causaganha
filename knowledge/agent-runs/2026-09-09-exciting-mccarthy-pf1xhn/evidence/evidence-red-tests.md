---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-pf1xhn-evidence-red-tests"
run_id: "2026-09-09-exciting-mccarthy-pf1xhn"
goal_id: "2026-09-09-exciting-mccarthy-pf1xhn-goal-juris-datajud-ia-fallback"
kind: "test_red"
reference: "tests/test_render_queries.py::test_register_datajud_capa_falls_back_to_ia_when_local_absent, ::test_register_tjro_juris_falls_back_to_ia_when_local_absent, ::test_register_tjro_juris_dedups_overlapping_ia_shards"
summary: "uv run pytest tests/test_render_queries.py -k 'datajud_capa_falls_back or tjro_juris_falls_back or tjro_juris_dedups' -> 3 failed, 41 deselected. Each fails with 'assert False is True': _register_datajud_capa/_register_tjro_juris return False (no view registered) even though a fake ensure_datajud_parquets()/ensure_juris_parquets() reports a real IA-fallback parquet -- reproducing exactly the production defect (the local-only glob never sees IA-fallback-shaped paths, whether from update-catalog.yml's reconcile-cache or a deploy-web.yml checkout that never runs reconcile_processos.py at all)."
---

# Evidência RED

Três testes novos falham antes da correção, reproduzindo exatamente o defeito de produção: `_register_tjro_juris`/`_register_datajud_capa` retornam `False` mesmo quando `ensure_juris_parquets()`/`ensure_datajud_parquets()` (falsificados no teste) reportam arquivos reais vindos do fallback de IA.
