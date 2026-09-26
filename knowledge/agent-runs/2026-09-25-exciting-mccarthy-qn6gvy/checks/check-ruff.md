---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-qn6gvy-check-ruff"
run_id: "2026-09-25-exciting-mccarthy-qn6gvy"
command: "uv run ruff check . && uv run ruff format --check ."
result: "passed"
summary: "Repositório inteiro limpo após rodar `ruff format` uma vez sobre service.py/test_service.py para corrigir formatação introduzida pelas novas funções/testes; ruff check e format --check ficam verdes em seguida."
---

# Check: ruff check + format --check (repositório inteiro)

`ruff check .` -> All checks passed!
`ruff format --check .` -> 461 files already formatted (após rodar `ruff format` uma vez sobre os dois arquivos tocados para corrigir formatação).
