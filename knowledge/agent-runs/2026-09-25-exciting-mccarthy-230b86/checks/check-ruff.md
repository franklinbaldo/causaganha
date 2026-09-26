---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-230b86-check-ruff"
run_id: "2026-09-25-exciting-mccarthy-230b86"
goal_id: "2026-09-25-exciting-mccarthy-230b86-goal-catalog-discovery-allowlist"
command: "uv run ruff check . && uv run ruff format --check ."
result: "passed"
evidence_id: "2026-09-25-exciting-mccarthy-230b86-evidence-red-discover-catalog-items"
summary: "'All checks passed!' no ruff check; 462 arquivos ja formatados no ruff format --check. Repositorio inteiro, apos a mudanca em scripts/generate_catalog.py e tests/test_archive_partitions.py."
---

# Check: ruff

`uv run ruff check .` e `uv run ruff format --check .` limpos em todo o
repositório após as mudanças desta rodada.
