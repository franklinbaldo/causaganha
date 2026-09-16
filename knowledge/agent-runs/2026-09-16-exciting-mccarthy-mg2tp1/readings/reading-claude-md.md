---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-mg2tp1-reading-claude-md"
run_id: "2026-09-16-exciting-mccarthy-mg2tp1"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Repo has two runtime surfaces (djen-backup sync engine in src/djen_backup, web dashboard in web/) plus the ML segmenter-dataset lineage (src/segmenter_dataset, scripts/, docs/rfc/0012) this round's continuity work belongs to. Style rules relevant here: ruff strict (no blind `except Exception` outside an ADR-0011 worker-pool bulkhead), TRY300/301/401 enforced, Python 3.12+ with `from __future__ import annotations`. Pre-commit checklist: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`. Nothing in CLAUDE.md is specific to RFC 0012/segmenter beyond general style; that context lives in docs/rfc/0012 and knowledge/backlog, read separately below."
---

# Leitura: CLAUDE.md

Regras de estilo (ruff estrito, TRY300/301/401, sem `except Exception` fora
de bulkhead documentado por ADR 0011) e checklist pre-commit (`ruff
check`, `ruff format --check`, `pytest -q`). Nada especifico da linhagem
do segmentador (RFC 0012) -- esse contexto vem de `docs/rfc/0012-*` e
`knowledge/backlog/`, lidos separadamente.
