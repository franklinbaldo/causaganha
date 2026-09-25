---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-r2xele-check-ruff"
run_id: "2026-09-25-exciting-mccarthy-r2xele"
command: "uv run ruff check . && uv run ruff format --check ."
result: "passed"
summary: "Repositorio inteiro limpo -- esta rodada nao tocou nenhum arquivo Python (mudanca inteiramente em web/src/lib/processoCnj.ts e nos relatorios OKF em knowledge/), mas o check e rodado por rotina antes de qualquer commit, conforme CLAUDE.md."
---

# Check: ruff (lint + format), repositorio inteiro

```
$ uv run ruff check .
All checks passed!
$ uv run ruff format --check .
458 files already formatted
```
