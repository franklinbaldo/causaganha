---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-1c8jcc-check-ruff"
run_id: "2026-09-24-exciting-mccarthy-1c8jcc"
command: "uv run ruff check . && uv run ruff format --check ."
result: "passed"
summary: "ruff check: All checks passed! ruff format --check: 458 arquivos ja formatados (apos rodar 'uv run ruff format tests/test_workflow_dispatch_injection.py' uma vez para aplicar a formatacao padrao do projeto ao novo arquivo de teste)."
---

# Check: ruff (lint + format)

```
$ uv run ruff check .
All checks passed!

$ uv run ruff format --check .
458 files already formatted
```
