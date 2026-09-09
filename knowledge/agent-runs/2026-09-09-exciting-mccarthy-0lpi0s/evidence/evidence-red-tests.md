---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-0lpi0s-evidence-red-tests"
run_id: "2026-09-09-exciting-mccarthy-0lpi0s"
goal_id: "2026-09-09-exciting-mccarthy-0lpi0s-goal-fixture-network-guard"
kind: "test_red"
reference: "tests/test_render_contract_fixture.py::test_block_real_network_blocks_urlopen, ::test_block_real_network_blocks_httpx, ::test_block_real_network_restores_originals_on_exit, ::test_render_fixture_fails_fast_when_a_source_input_is_missing"
summary: "uv run pytest tests/test_render_contract_fixture.py -q, before scripts/render_contract_fixture.py had _block_real_network/RealNetworkAccessError: 4 failed, 1 passed. All 4 failures are AttributeError (module 'scripts.render_contract_fixture' has no attribute '_block_real_network' / 'RealNetworkAccessError'). The 5th test (end-to-end render_fixture(), no guard dependency) already passed, as expected since it exercises pre-existing behavior untouched by this goal."
---

# Evidência RED

`uv run pytest tests/test_render_contract_fixture.py -q` antes da implementação: 4 falhas por `AttributeError`, todas pela ausência da guarda ainda não implementada.
