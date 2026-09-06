---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-rvjn2w-evidence-green-bounded-cnj-fallback"
run_id: "2026-09-06-exciting-mccarthy-rvjn2w"
goal_id: "2026-09-06-exciting-mccarthy-rvjn2w-goal-bounded-cnj-fallback"
kind: "test_green"
reference: "uv run pytest tests/causaganha_mcp/test_decisoes_buscar.py -v (after src/causaganha_mcp/tools/decisoes.py changed)"
summary: "16 passed, 0 failed. _narrow_juris_datasets_for_cnj now raises IndiceProcessualUnavailableError instead of swallowing it into an unnarrowed return. The tool call site (decisoes_buscar) now only attempts narrowing when fonte in {'todas', 'juris'} (juris is otherwise absent from datasets anyway) and, on IndiceProcessualUnavailableError, always drops juris datasets before deciding: fonte='juris' raises ToolError with a message matching '[íÍ]ndice' (search_decisions never called — proven by a test double that calls pytest.fail if invoked); fonte='todas' appends a 'JURIS indisponível' limitation and forwards the request with plan.juris empty (0 of 1200 synthetic URLs reach the search plan) while stj results pass through unaffected. The pre-existing index-miss test (resolve_juris_urls_for_cnj returning [] without raising) keeps passing unmodified, and a new test confirms it adds no 'indisponível' limitation, keeping the two failure modes distinguishable in the response as #1241 requires."
---

# GREEN: fallback agora fica bounded

Os 16 testes de `test_decisoes_buscar.py` passam. `_narrow_juris_datasets_for_cnj` propaga `IndiceProcessualUnavailableError`; o site de chamada trata `fonte="juris"` com `ToolError` explícito (sem chamar `search_decisions`) e `fonte="todas"` omitindo JURIS com uma limitação registrada, preservando STJ. O caso de ausência real (índice acessível, CNJ sem registro) continua sem levantar exceção e sem gerar a limitação de indisponibilidade.
