---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-r0zxiq-check-ruff"
run_id: "2026-09-25-exciting-mccarthy-r0zxiq"
goal_id: "2026-09-25-exciting-mccarthy-r0zxiq-goal-datajud-kv-metadata"
command: "uv run ruff check src/datajud/archive.py src/datajud/service.py src/causaganha/processos/service.py tests/datajud/test_datajud_archive.py tests/causaganha/processos/test_service.py tests/test_reconcile_processos.py && uv run ruff format --check <mesmos arquivos>"
result: "passed"
evidence_id: "2026-09-25-exciting-mccarthy-r0zxiq-evidence-green-datajud-write-side"
summary: "`ruff check` reportou 'All checks passed!' nos 6 arquivos tocados. `ruff format --check` apontou 1 arquivo (`tests/causaganha/processos/test_service.py`) fora de formato; corrigido com `uv run ruff format` e reverificado limpo."
---

# Check: ruff (lint + format)
