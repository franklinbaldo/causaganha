---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-5lvbii-reading-claude-md"
run_id: "2026-09-16-exciting-mccarthy-5lvbii"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces (Python backend in src/causaganha and src/djen_backup, web frontend in web/). Key correctness rules for djen-backup: djen_raw is the raw HTTP status, never a verdict; availability requires HTTP 200 AND a download URL in the body (a 200 with 'Sem comunicacoes' is absent, same as 404); never treat 403 as absent (rate limiting); sync-manifest.parquet on IA is the sole source of truth, sync-manifest.csv is retired. Style: ruff strict, no blind except Exception outside the ADR-0011 worker-pool bulkhead pattern, TRY300/301/401 enforced, Python 3.12+ with `from __future__ import annotations`. Pre-commit checklist: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`. Nothing in CLAUDE.md is specific to the segmenter/RFC 0012 lineage that today's open PR (#1562) and issue #1050/#1051 belong to -- that context lives in docs/rfc/0012-* and knowledge/backlog/issue-1050.md, read separately below."
---

# Leitura: CLAUDE.md

Regras de correção do djen-backup (djen_raw é status bruto, não veredito;
disponibilidade exige 200 + URL de download no corpo; nunca tratar 403
como ausente; sync-manifest.parquet é a fonte única de verdade) e estilo
(ruff estrito, TRY300/301/401, sem `except Exception` fora de bulkhead
documentado por ADR 0011). Checklist pre-commit: `ruff check`, `ruff
format --check`, `pytest -q`. Nada específico da linhagem do segmentador
(RFC 0012) que domina o trabalho ativo de hoje -- esse contexto vem de
`docs/rfc/0012-*` e `knowledge/backlog/issue-1050.md`, lidos separadamente.
