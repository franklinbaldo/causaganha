---
type: AgentDecision
id: "2026-09-09-exciting-mccarthy-0lpi0s-decision-unify-patch-restore"
run_id: "2026-09-09-exciting-mccarthy-0lpi0s"
goal_id: "2026-09-09-exciting-mccarthy-0lpi0s-goal-fixture-network-guard"
question: "While adding the network guard, an in-process regression test of render_fixture() exposed that it permanently overwrites renderer._register_comunicacoes and reconcile_processos.ensure_juris_parquets/ensure_datajud_parquets with no restore (harmless only because it had only ever run as a subprocess before). Fix that leak as part of this goal, or file it separately and only add the network guard?"
choice: "Fix it now, in this same change: introduce one save-and-restore context manager (_patched_attrs) and route every cross-module monkeypatch render_fixture() makes through it, replacing the bare reassignments."
rationale: "Reproduced concretely: running tests/test_render_contract_fixture.py before tests/test_render_queries.py in one pytest session broke test_register_comunicacoes_prefers_indice_when_available and its falls_back sibling (rows == [] instead of the expected row) -- confirmed absent on unmodified main via git stash, so this was a real regression risk, not a pre-existing flake. This is exactly the class of bug the round's own goal targets -- an isolation mechanism that looks contained but leaks -- so fixing it here is the more complete answer to the same goal statement, not scope creep into a separate goal. Deferring it would have shipped a network guard on top of a monkeypatching mechanism just shown to be unsafe to call in-process, which is precisely how a future test (this file's own newest tests) could reintroduce the same class of cross-test pollution the fix removes."
---

# Decisão: um único mecanismo de patch/restore

Ao escrever o primeiro teste de regressão da guarda (uma chamada in-process end-to-end a `render_fixture()`), descobri que a reatribuição direta pré-existente vazava permanentemente para o resto do processo pytest -- corrompendo dois testes de `tests/test_render_queries.py` sempre que rodassem depois deste arquivo na mesma sessão (confirmado ausente na `main` sem modificação). Corrigido com um único `_patched_attrs` que salva e restaura tudo, dentro do mesmo goal, por ser a mesma classe de problema que o goal já visava.
