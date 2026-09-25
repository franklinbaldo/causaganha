---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-o3ubcj-check-ruff"
run_id: "2026-09-25-exciting-mccarthy-o3ubcj"
command: "uv run ruff check . && uv run ruff format --check ."
result: "passed"
summary: "Nenhum arquivo Python tocado nesta rodada (o goal é inteiramente TypeScript, em web/src/lib/processoCnj.ts); ruff check e format --check ficam verdes trivialmente. `ruff check .` -> All checks passed! `ruff format --check .` -> 461 files already formatted."
---

# Check: ruff check + format --check (repositório inteiro)
