---
type: AgentEvidence
id: "2026-09-07-exciting-mccarthy-cctnlf-evidence-red-tribunais-merge"
run_id: "2026-09-07-exciting-mccarthy-cctnlf"
goal_id: "2026-09-07-exciting-mccarthy-cctnlf-goal-tribunal-list-merge"
kind: "test_red"
reference: "tests/djen_backup/test_tribunais.py (new file, 5 tests)"
summary: "Ran `TRIBUNAL=tjro uv run pytest tests/djen_backup/test_tribunais.py -q` against the unmodified src/djen_backup/tribunais.py. 2 of 5 tests fail exactly as predicted by the goal: test_get_tribunal_list_merges_new_api_codes_into_the_hardcoded_baseline fails with `assert 'TJRO' in ['TJXX']` (the mocked API response, containing only 'TJXX', silently replaced the entire result instead of adding to it), and test_get_tribunal_list_never_returns_fewer_than_the_hardcoded_baseline fails with `assert {96 hardcoded codes} <= {'TJXX'}`. The other 3 tests (empty-API-response fallback, API-error fallback, fetch_tribunal_list_from_api's raw parsing) already pass against today's code, confirming the test file isolates exactly the merge defect and does not accidentally assert new behavior for paths that already work."
---

# Evidência RED: get_tribunal_list não faz merge

`tests/djen_backup/test_tribunais.py` escrito antes de qualquer mudança em `tribunais.py`. 2/5 testes falham confirmando o defeito: uma resposta parcial da API (`['TJXX']`) descarta os 96 tribunais hardcoded em vez de somar a eles. Os 3 testes de fallback (API vazia, API com erro, parsing bruto) já passam, isolando exatamente o comportamento a corrigir.
