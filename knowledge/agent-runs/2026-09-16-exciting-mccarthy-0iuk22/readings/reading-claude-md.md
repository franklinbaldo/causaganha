---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-0iuk22-reading-claude-md"
run_id: "2026-09-16-exciting-mccarthy-0iuk22"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Repo has two runtime surfaces (djen-backup sync engine in src/djen_backup, web dashboard in web/) plus a growing ML surface (segmenter/OPF training under src/segmenter_dataset, scripts/, docs/rfc/0012). Style rules relevant to this round: ruff strict (no blind except Exception outside worker-pool bulkheads per ADR 0011), TRY300/301/401 enforced, Python 3.12+ with `from __future__ import annotations`. Before committing: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`. Nothing in CLAUDE.md is specific to the segmenter dataset lineage (RFC 0012) beyond general style -- that context lives in docs/rfc/0012 and knowledge/backlog, read separately."
---

# Leitura: CLAUDE.md

Confirma as regras de estilo (ruff estrito, TRY300/301/401, sem `except
Exception` fora de bulkhead documentado por ADR 0011) e o checklist
pre-commit (`ruff check`, `ruff format --check`, `pytest -q`). Nada aqui e
especifico da linhagem do segmentador (RFC 0012) -- esse contexto vem de
`docs/rfc/0012-segmenter-dataset-confiavel-baseline.md` e
`knowledge/backlog/`, lidos separadamente nesta rodada.
