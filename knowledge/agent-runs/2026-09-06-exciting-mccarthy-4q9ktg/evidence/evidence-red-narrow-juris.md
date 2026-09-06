---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-4q9ktg-evidence-red-narrow-juris"
run_id: "2026-09-06-exciting-mccarthy-4q9ktg"
goal_id: "2026-09-06-exciting-mccarthy-4q9ktg-goal-cnj-lookup-bounded-scan"
kind: "test_red"
reference: "git stash push -- src/causaganha_mcp/tools/decisoes.py && uv run pytest tests/causaganha_mcp/test_decisoes_buscar.py -q -k 'narrows_juris_scan or falls_back_to_full_scan'; uv run pytest tests/causaganha/decisoes/test_published.py -q (before published.py defined resolve_juris_urls_for_cnj)"
summary: "Before the fix, the two new integration tests in tests/causaganha_mcp/test_decisoes_buscar.py fail (AttributeError: module has no attribute resolve_juris_urls_for_cnj) because decisoes.py never imported or called the resolver, confirmed by stashing the decisoes.py change and re-running just those two tests; the three new unit tests in tests/causaganha/decisoes/test_published.py fail at collection (ImportError) before published.py defines resolve_juris_urls_for_cnj/IndiceProcessualUnavailableError."
---

# Evidência RED

```
git stash push -- src/causaganha_mcp/tools/decisoes.py
uv run pytest tests/causaganha_mcp/test_decisoes_buscar.py -q -k "narrows_juris_scan or falls_back_to_full_scan"
```
```
AttributeError: <module 'causaganha_mcp.tools.decisoes' ...> has no attribute 'resolve_juris_urls_for_cnj'
FAILED tests/causaganha_mcp/test_decisoes_buscar.py::test_cnj_lookup_narrows_juris_scan_to_the_indexed_file
FAILED tests/causaganha_mcp/test_decisoes_buscar.py::test_cnj_lookup_falls_back_to_full_scan_when_index_unavailable
```

Separadamente, antes de implementar `published.py`:
```
uv run pytest tests/causaganha/decisoes/test_published.py -q
```
```
ImportError: cannot import name 'IndiceProcessualUnavailableError' from 'causaganha.decisoes.published'
Interrupted: 1 error during collection
```

`git stash pop` restaurou a correção logo em seguida (ver evidence-green-narrow-juris).
