---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-la7bsl-reading-claude-md"
run_id: "2026-09-16-exciting-mccarthy-la7bsl"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Repo has two runtime surfaces (djen-backup sync engine in src/djen_backup, web dashboard in web/); the segmenter-dataset lineage (src/segmenter_dataset, scripts/, docs/rfc/0012) this round's continuity work belongs to is not itself described in CLAUDE.md beyond general Python style rules. Relevant rules for this round: ruff strict (no blind `except Exception` outside an ADR-0011 worker-pool bulkhead), TRY300/301/401 enforced, Python 3.12+ with `from __future__ import annotations`, pre-commit checklist `uv run ruff check` / `uv run ruff format --check` / `uv run pytest -q`. Nothing here changes this round's plan; segmenter-specific context lives in docs/rfc/0012 and knowledge/backlog, confirmed separately in the OKF reading below."
---

# Leitura: CLAUDE.md

Regras de estilo gerais (ruff estrito, TRY300/301/401, `from __future__
import annotations`, checklist pre-commit `ruff check` / `ruff format
--check` / `pytest -q`). Nada especifico da linhagem do segmentador (RFC
0012) -- esse contexto vem de `docs/rfc/0012-*` e `knowledge/backlog/`.
