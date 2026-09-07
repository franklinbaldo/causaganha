---
type: AgentEvidence
id: "2026-09-07-exciting-mccarthy-kfv7sx-evidence-green-mcp-profiles"
run_id: "2026-09-07-exciting-mccarthy-kfv7sx"
goal_id: "2026-09-07-exciting-mccarthy-kfv7sx-goal-mcp-public-profile"
kind: "test_green"
reference: "src/causaganha_mcp/profiles.py; src/causaganha_mcp/tools/datajud.py (register split into register_status/register_facetas); src/causaganha_mcp/server.py; tests/causaganha_mcp/test_mcp_profiles.py; tests/causaganha_mcp/test_web_agents_contract.py"
summary: "uv run pytest tests/causaganha_mcp/test_mcp_profiles.py -q: 4/4 passed, once causaganha_mcp/profiles.py (build_public_server/build_operator_server, PUBLIC_TOOL_NAMES/OPERATOR_ONLY_TOOL_NAMES) exists and datajud.py's register() is split into register_status/register_facetas. Full tests/causaganha_mcp/ directory: 249 passed (no regression from switching test_web_agents_contract.py's parity gate from build_server() to build_public_server()). Full repo pytest -q: exactly one FAILED (tests/test_check_agent_run_completeness.py::test_main_over_this_rounds_own_report_tree_is_complete, expected while this round's own run.md is still mid-draft), everything else green — including test_readme_catalog_contract.py, test_agent_catalog_contract.py and test_tool_schema.py, which still assert against build_server()'s now-wrapped catalog unchanged."
---

# GREEN: perfil MCP público implementado

`tests/causaganha_mcp/test_mcp_profiles.py`: 4/4 verde. `tests/causaganha_mcp/`: 249 verde (sem regressão ao trocar o gate de paridade de `/agentes` para `build_public_server()`). `pytest -q` no repo inteiro: única falha é o teste de completude deste próprio relatório (esperado, rodada em andamento) — todo o resto, incluindo os testes que ancoram no catálogo completo de `build_server()` (README, catálogo de agente, schema), continua verde sem alteração.
