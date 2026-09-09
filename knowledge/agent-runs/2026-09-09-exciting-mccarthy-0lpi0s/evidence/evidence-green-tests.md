---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-0lpi0s-evidence-green-tests"
run_id: "2026-09-09-exciting-mccarthy-0lpi0s"
goal_id: "2026-09-09-exciting-mccarthy-0lpi0s-goal-fixture-network-guard"
kind: "test_green"
reference: "tests/test_render_contract_fixture.py (6 tests, final)"
summary: "uv run pytest tests/test_render_contract_fixture.py -q: 6 passed. Covers: _block_real_network blocks urllib.request.urlopen and httpx.Client.send with RealNetworkAccessError; restores both on exit; render_fixture() raises RealNetworkAccessError immediately (not: hangs, times out, or silently degrades) when a source's local fixture input is deleted after _write_fixtures(); the existing end-to-end render_fixture() call still succeeds and never touches the network; and (added after discovering the state-leak bug, see decision-unify-patch-restore) render_fixture() no longer permanently overwrites renderer._register_comunicacoes / reconcile_processos.ensure_juris_parquets / reconcile_processos.ensure_datajud_parquets / renderer.ROOT for the rest of the process."
---

# Evidência GREEN

`uv run pytest tests/test_render_contract_fixture.py -q`: 6 aprovados, cobrindo a guarda de rede e a não-vazamento de estado do patch.
