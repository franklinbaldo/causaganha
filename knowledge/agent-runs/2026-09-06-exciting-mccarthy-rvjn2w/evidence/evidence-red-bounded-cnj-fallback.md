---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-rvjn2w-evidence-red-bounded-cnj-fallback"
run_id: "2026-09-06-exciting-mccarthy-rvjn2w"
goal_id: "2026-09-06-exciting-mccarthy-rvjn2w-goal-bounded-cnj-fallback"
kind: "test_red"
reference: "uv run pytest tests/causaganha_mcp/test_decisoes_buscar.py -v -k 'index_unavailable or index_miss' (before src/causaganha_mcp/tools/decisoes.py changed)"
summary: "2 failed, 1 passed, 13 deselected. test_cnj_lookup_fonte_juris_fails_bounded_when_index_unavailable failed because search_decisions was actually invoked with all 1200 synthetic JURIS URLs in plan.juris — proving the current except IndiceProcessualUnavailableError branch really does fall back to the full unnarrowed dataset list. test_cnj_lookup_fonte_todas_omits_juris_but_keeps_other_sources_when_index_unavailable failed because captured['juris_urls'] held all 1200 synthetic URLs instead of []. The third new test, test_cnj_index_miss_is_real_absence_not_unavailability, already passed unmodified — confirming the genuine-index-miss path (resolve_juris_urls_for_cnj returning [] without raising) is unaffected by this change and needs no fix."
---

# RED: fallback ainda devolve a lista JURIS inteira

Os dois novos testes de `fonte="juris"` e `fonte="todas"` falham contra a implementação atual: `search_decisions` recebe as 1200 URLs JURIS sintéticas inteiras quando o índice está indisponível, confirmando que `_narrow_juris_datasets_for_cnj` ainda cai no scan sem bound que #1241 pede para eliminar. O teste de ausência real (índice disponível, CNJ sem registro) já passa sem alteração.
