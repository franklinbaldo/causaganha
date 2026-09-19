---
type: AgentCheck
id: "2026-09-19-exciting-mccarthy-gbf44b-check-ruff"
run_id: "2026-09-19-exciting-mccarthy-gbf44b"
command: "uv run ruff check && uv run ruff format --check"
result: "passed"
evidence_id: null
summary: "All checks passed; 454 files already formatted."
---

# Check: ruff

Rodado apos a ingestao do lote 22 (documentos XML nao sao alvo do ruff,
mas o comando roda sobre todo o repositorio por habito de disciplina do
CLAUDE.md).
