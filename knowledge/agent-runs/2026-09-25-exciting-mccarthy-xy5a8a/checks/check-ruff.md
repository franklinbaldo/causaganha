---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-xy5a8a-check-ruff"
run_id: "2026-09-25-exciting-mccarthy-xy5a8a"
goal_id: "2026-09-25-exciting-mccarthy-xy5a8a-goal-processo-consultar-evidence-marker"
command: "uv run ruff check src/causaganha_mcp/tools/processo.py tests/causaganha_mcp/test_untrusted_evidence_marker.py && uv run ruff format --check src/causaganha_mcp/tools/processo.py tests/causaganha_mcp/test_untrusted_evidence_marker.py"
result: "passed"
evidence_id: "2026-09-25-exciting-mccarthy-xy5a8a-evidence-green-processo-consultar-marker"
summary: "ruff check reportou 'All checks passed!' e ruff format --check reportou os 2 arquivos tocados ja formatados corretamente."
---

# Check: ruff lint + format

`ruff check` reportou "All checks passed!" e `ruff format --check`
reportou os 2 arquivos tocados já formatados corretamente.
