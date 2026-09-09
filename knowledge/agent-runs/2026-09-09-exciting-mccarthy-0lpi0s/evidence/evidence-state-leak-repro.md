---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-0lpi0s-evidence-state-leak-repro"
run_id: "2026-09-09-exciting-mccarthy-0lpi0s"
goal_id: "2026-09-09-exciting-mccarthy-0lpi0s-goal-fixture-network-guard"
kind: "runtime"
reference: "uv run pytest tests/test_render_contract_fixture.py tests/test_render_queries.py -q, before decision-unify-patch-restore's fix, vs. git-stash baseline on unmodified main"
summary: "Before unifying the patch/restore mechanism, running the new fixture test file together with tests/test_render_queries.py in one pytest session reproduced 2 failures: test_register_comunicacoes_falls_back_to_catalog_manifest_when_indice_missing and test_register_comunicacoes_prefers_indice_when_available, both asserting rows == [('00000010220248220001',)] but getting []. Confirmed on unmodified main (git stash) that both tests pass in isolation -- the failure was a genuine regression from render_fixture()'s bare, unrestored reassignment of renderer._register_comunicacoes leaking across tests in the same process. After applying _patched_attrs, the same two-file run passes cleanly (51 passed)."
---

# Evidência: reprodução do vazamento de estado

Rodar `tests/test_render_contract_fixture.py` seguido de `tests/test_render_queries.py` na mesma sessão pytest quebrava dois testes de `_register_comunicacoes` (confirmado ausente na `main` sem modificação, via `git stash`). Corrigido depois de unificar o patch/restore; a mesma combinação de arquivos passa limpa.
