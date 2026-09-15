---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-wvzu11-check-ruff"
run_id: "2026-09-15-exciting-mccarthy-wvzu11"
command: "uv run ruff check . && uv run ruff format --check ."
result: "passed"
evidence_id: "2026-09-15-exciting-mccarthy-wvzu11-evidence-green-test"
summary: "ruff check: All checks passed!. ruff format --check: 442 files already formatted (após uma formatação automática do arquivo de teste novo)."
---

# Check: ruff (lint + format) no repositório inteiro

`uv run ruff check .` -> "All checks passed!". `uv run ruff format --check .` -> "442 files already formatted" (após rodar `ruff format` uma vez no arquivo de teste novo, que precisou de uma quebra de linha).
