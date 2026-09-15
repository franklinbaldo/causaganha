---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-5ov0kv-check-ruff"
run_id: "2026-09-15-exciting-mccarthy-5ov0kv"
goal_id: null
command: "uv run ruff check && uv run ruff format --check"
result: "passed"
evidence_id: null
summary: "'All checks passed!' / '446 files already formatted'."
---

# Check: ruff check + ruff format --check

Nenhum arquivo Python foi tocado diretamente nesta rodada (o trabalho de
dominio e dados XML sob `data/segmenter/`), mas o piso de pre-commit do
CLAUDE.md exige rodar ambos antes de qualquer push. `uv run ruff check`:
"All checks passed!". `uv run ruff format --check`: "446 files already
formatted".
