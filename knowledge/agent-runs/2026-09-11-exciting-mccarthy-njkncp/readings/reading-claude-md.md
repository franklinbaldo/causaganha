---
type: AgentReading
id: "2026-09-11-exciting-mccarthy-njkncp-reading-claude-md"
run_id: "2026-09-11-exciting-mccarthy-njkncp"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Read in full via the system-provided project instructions. Two runtime surfaces: Python backend (src/causaganha, src/djen_backup) and web frontend (web/, Astro 7 + Svelte 5). Correctness rules directly relevant to today's ongoing lineage of rounds: djen_raw is the raw HTTP transport code, never a verdict on availability; genuine absent is 404, 400 (holiday), or HTTP 200 with body 'Sem comunicações' (no download URL); djen_raw='200'+djen_status='available' is NOT self-consistent proof historically (~79K legacy rows from a body-blind checker, fixed by promoting sync-manifest.parquet to sole source of truth). sync-manifest.parquet on IA is the single source of truth; sync-manifest.csv is a derived export only, nothing reads it as canonical. Style rules: no blind `except Exception` outside the documented per-item worker-loop bulkhead (ADR 0011, must cite it); TRY300/TRY301/TRY401 enforced; ruff strict; Python 3.12+, `from __future__ import annotations`. CSS token boundary: Panda CSS via cobogo preset is the one design system; three legacy Svelte islands (ProcessoLookup, PublicationSearch, SavedConsultations) keep --papel-*/--s-* aliases, no new bespoke custom properties. Before committing: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`. Nothing changed relative to what today's prior rounds (r3erpr, aezdb9, yd5lu0, 41w39p, 25og4b, 8042ey) recorded; this reading independently re-verified the file against the current working tree at HEAD e5fee06, not just memory of prior rounds' summaries."
---

# Leitura de CLAUDE.md

Leitura completa das instruções de projeto. Reconfirma as regras de correção sobre `djen_raw`/`djen_status`/403-nunca-ausente e o `sync-manifest.parquet` como fonte única de verdade -- regras que motivaram várias das seis rodadas anteriores de hoje (03/09-10/09). Regras de estilo (ruff estrito, TRY300/301/401, bulkhead da ADR 0011, fronteira de tokens CSS Panda/cobogó) confirmadas sem divergência em relação ao HEAD atual (e5fee06).
