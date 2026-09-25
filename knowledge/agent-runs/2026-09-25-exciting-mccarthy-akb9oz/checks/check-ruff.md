---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-akb9oz-check-ruff"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
command: "uv run ruff check && uv run ruff format --check"
result: "passed"
summary: "Nenhum arquivo Python foi tocado nesta rodada (trabalho inteiramente em web/src/layouts, web/src/pages, web/src/lib -- TypeScript/Astro). Rodado mesmo assim como verificacao de que o repositorio inteiro permanece limpo apos o merge de #1627 (que tocou src/causaganha_mcp/evidence.py) incorporado via git merge origin/main."
---

# Check: ruff check + ruff format --check, repositorio inteiro

```
$ uv run ruff check
All checks passed!

$ uv run ruff format --check
460 files already formatted
```
