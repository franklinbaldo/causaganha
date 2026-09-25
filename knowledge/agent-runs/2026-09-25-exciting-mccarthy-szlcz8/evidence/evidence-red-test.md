---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-szlcz8-evidence-red-test"
run_id: "2026-09-25-exciting-mccarthy-szlcz8"
goal_id: "2026-09-25-exciting-mccarthy-szlcz8-goal-juris-discovery-allowlist"
kind: "test_red"
reference: "tests/test_reconcile_processos.py::TestDiscoverJurisItemsAllowlist (5 testes novos)"
summary: "uv run pytest -q tests/test_reconcile_processos.py -k TestDiscoverJurisItemsAllowlist contra a implementação anterior de _discover_juris_items: os 5 testes novos falham por respx.models.AllMockedAssertionError — a implementação antiga chama GET https://archive.org/advancedsearch.php?q=identifier:tjro-juris-*&... (busca livre não-autenticada), rota que os novos testes deliberadamente não mockam (só mockam o manifesto do projeto). Falha pela razão certa: a chamada HTTP real que o goal exige eliminar, não um erro de fixture."
---

# Evidência: RED confirmado (5/5 falhas pela razão certa)
