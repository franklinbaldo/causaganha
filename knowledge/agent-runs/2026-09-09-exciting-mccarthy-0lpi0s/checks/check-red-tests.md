---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-0lpi0s-check-red-tests"
run_id: "2026-09-09-exciting-mccarthy-0lpi0s"
goal_id: "2026-09-09-exciting-mccarthy-0lpi0s-goal-fixture-network-guard"
command: "uv run pytest tests/test_render_contract_fixture.py -q"
result: "failed"
evidence_id: "2026-09-09-exciting-mccarthy-0lpi0s-evidence-red-tests"
summary: "4 of 5 tests failed with AttributeError before scripts/render_contract_fixture.py had _block_real_network/RealNetworkAccessError -- confirms the tests actually exercise the not-yet-written guard, not a tautology."
---

# Check: testes RED

4 de 5 testes falhavam com `AttributeError` antes da implementação da guarda.
