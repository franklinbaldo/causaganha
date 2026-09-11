---
type: AgentReading
id: "2026-09-11-exciting-mccarthy-qpktqe-reading-claude-md"
run_id: "2026-09-11-exciting-mccarthy-qpktqe"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Read in full via the system-provided project instructions at branch start (HEAD 24eefd1). Two runtime surfaces: Python backend (src/causaganha, src/djen_backup) and web frontend (web/, Astro 7 + Svelte 5). djen-backup: sync-manifest.parquet on IA is the sole source of truth (compacted from append-only manifest-log/*.csv segments); sync-manifest.csv is a derived export only, never read as canonical. djen_raw is the raw HTTP transport code ('200'/'404'/'400'/'403'/'timeout'/'network'), never a verdict on availability -- genuine absent is 404, 400 (holiday), or HTTP 200 with body 'Sem comunicações' (no download URL); a bare 200 is not proof of availability. Never treat 403 as absent (CloudFront/WAF rate-limiting). ~79K legacy rows were mis-recorded available under the old checker; don't trust old 'absent' entries without live verification. Engine runs 3 independent worker pools (checkers/downloaders/uploaders); IA items use djen-{tribunal}-{year} naming. Style: ruff strict, no blind `except Exception` outside the ADR-0011 per-item worker-loop bulkhead, TRY300/TRY301/TRY401 enforced, Python 3.12+ with `from __future__ import annotations`. CSS token boundary: Panda CSS via the cobogo preset is the one design system; three legacy Svelte islands (ProcessoLookup, PublicationSearch, SavedConsultations) keep --papel-*/--s-* aliases and must not gain new bespoke custom properties. Before committing: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`. No divergence from what the immediately preceding round (vd5dfq) recorded."
---

# Leitura de CLAUDE.md

Leitura completa e reconfirmada contra o HEAD de início de branch (`24eefd1`, após o merge de #1456). Sem divergência das regras já registradas pela rodada anterior (`vd5dfq`): `djen_raw`/`djen_status`, `sync-manifest.parquet` como fonte única de verdade, estilo ruff estrito, fronteira Panda/cobogó.
