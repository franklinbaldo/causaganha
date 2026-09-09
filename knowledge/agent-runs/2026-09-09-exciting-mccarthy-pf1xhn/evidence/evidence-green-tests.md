---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-pf1xhn-evidence-green-tests"
run_id: "2026-09-09-exciting-mccarthy-pf1xhn"
goal_id: "2026-09-09-exciting-mccarthy-pf1xhn-goal-juris-datajud-ia-fallback"
kind: "test_green"
reference: "tests/test_render_queries.py -k 'datajud_capa_falls_back or tjro_juris_falls_back or tjro_juris_dedups'; tests/test_render_queries.py (full file); uv run pytest -q (full suite)"
summary: "After delegating _register_datajud_capa/_register_tjro_juris to reconcile_processos.ensure_datajud_parquets()/ensure_juris_parquets(): the 3 targeted tests -> 3 passed, 41 deselected. Full tests/test_render_queries.py -> 44 passed. Full repo suite (uv run pytest -q) -> only the expected, known-transient failure remains (tests/test_check_agent_run_completeness.py::test_main_over_this_rounds_own_report_tree_is_complete, because this run.md is still in draft with empty completed_at/decision_ids/evidence_ids/next_move/result_summary at the time this check ran — resolved by this same round's closing commit). No other regression. ruff check and ruff format --check both pass on scripts/render_queries.py and tests/test_render_queries.py."
---

# Evidência GREEN

Os três testes-alvo passam após a correção. O arquivo de testes completo (44 testes) passa. A suíte completa do repositório só mostra a falha esperada e transitória do próprio gate de completude do `AgentRun` em rascunho — resolvida no fechamento desta rodada.
