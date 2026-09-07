---
type: AgentEvidence
id: "2026-09-07-exciting-mccarthy-kfv7sx-evidence-red-mcp-profiles"
run_id: "2026-09-07-exciting-mccarthy-kfv7sx"
goal_id: "2026-09-07-exciting-mccarthy-kfv7sx-goal-mcp-public-profile"
kind: "test_red"
reference: "tests/causaganha_mcp/test_mcp_profiles.py"
summary: "uv run pytest tests/causaganha_mcp/test_mcp_profiles.py -q fails at collection: ModuleNotFoundError: No module named 'causaganha_mcp.profiles' (raised importing PUBLIC_TOOL_NAMES/OPERATOR_ONLY_TOOL_NAMES/build_public_server/build_operator_server, none of which exist yet). Written before any implementation, per TDD: the four tests declare the desired contract (public profile == exact product tool set, no public tool exposes a local path argument, datajud_status is operator-only, the operator profile matches today's build_server() catalog exactly)."
---

# RED: contrato do perfil MCP público ainda não existe

`pytest tests/causaganha_mcp/test_mcp_profiles.py` falha na coleta com `ModuleNotFoundError: No module named 'causaganha_mcp.profiles'` — o módulo e as quatro asserções do contrato (catálogo público exato, nenhum parâmetro de caminho local no público, `datajud_status` só no operador, perfil operador idêntico ao `build_server()` atual) ainda não têm implementação.
