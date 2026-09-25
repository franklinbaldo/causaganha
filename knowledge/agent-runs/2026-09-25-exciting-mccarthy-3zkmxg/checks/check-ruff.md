---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-3zkmxg-check-ruff"
run_id: "2026-09-25-exciting-mccarthy-3zkmxg"
command: "uv run ruff check . && uv run ruff format --check ."
result: "passed"
summary: "Repositorio inteiro limpo apos a mudanca. Uma violacao TRY301 foi encontrada e corrigida durante a rodada (raise dentro do try em download_zip extraido para a funcao interna _raise_too_large), e ruff format --check exigiu uma reformatacao (aplicada com ruff format) antes de ficar limpo."
---

# Check: ruff (lint + format) apos implementar orcamentos de ZIP

```
$ uv run ruff check .
All checks passed!
$ uv run ruff format --check .
458 files already formatted
```
