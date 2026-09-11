---
type: AgentReading
id: "2026-09-11-exciting-mccarthy-vd5dfq-reading-claude-md"
run_id: "2026-09-11-exciting-mccarthy-vd5dfq"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Read in full via the system-provided project instructions at HEAD f2ac680. Two runtime surfaces: Python backend (src/causaganha, src/djen_backup) and web frontend (web/, Astro 7 + Svelte 5). Correctness rules load-bearing for this lineage's recent rounds: djen_raw is the raw HTTP transport code, never a verdict on availability; genuine absent is 404, 400 (holiday), or HTTP 200 with body 'Sem comunicações' (no download URL); djen_raw='200'+djen_status='available' is NOT self-consistent proof historically. sync-manifest.parquet on IA is the single source of truth; sync-manifest.csv is a derived export only. Style: no blind `except Exception` outside the ADR-0011 per-item worker-loop bulkhead; TRY300/TRY301/TRY401 enforced; ruff strict; Python 3.12+, `from __future__ import annotations`. CSS token boundary: Panda CSS via cobogo preset is the one design system; three legacy Svelte islands keep --papel-*/--s-* aliases. Before committing: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`. No divergence from what njkncp (the immediately preceding round, HEAD e5fee06) recorded -- verified directly against the current working tree, not from memory of prior summaries."
---

# Leitura de CLAUDE.md

Leitura completa e reconfirmada contra o HEAD atual (`f2ac680`, após o merge da PR de fechamento #1455 desta manhã). Sem divergência das regras já registradas por `njkncp`: `djen_raw`/`djen_status`, `sync-manifest.parquet` como fonte única de verdade, estilo ruff estrito, fronteira Panda/cobogó.
