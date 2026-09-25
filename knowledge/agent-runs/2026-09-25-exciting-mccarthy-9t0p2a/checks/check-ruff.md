---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-9t0p2a-check-ruff"
run_id: "2026-09-25-exciting-mccarthy-9t0p2a"
command: "uv run ruff check . && uv run ruff format --check ."
result: "passed"
evidence_id: "2026-09-25-exciting-mccarthy-9t0p2a-evidence-green-untrusted-evidence-marker"
summary: "Repositorio inteiro limpo apos as mudancas em src/causaganha_mcp/evidence.py (novo), src/causaganha_mcp/tools/publicacoes.py e src/causaganha_mcp/tools/decisoes.py."
---

# Check: ruff (lint + format), repositorio inteiro

```
$ uv run ruff check .
All checks passed!
$ uv run ruff format --check .
460 files already formatted
```
