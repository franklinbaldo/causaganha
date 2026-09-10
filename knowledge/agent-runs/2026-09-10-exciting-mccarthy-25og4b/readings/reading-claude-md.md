---
type: AgentReading
id: "2026-09-10-exciting-mccarthy-25og4b-reading-claude-md"
run_id: "2026-09-10-exciting-mccarthy-25og4b"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Read in full via the system-provided project instructions. Two runtime surfaces: Python backend (src/causaganha, src/djen_backup) and web frontend (web/, Astro+Svelte). Correctness rules: djen_raw is the raw HTTP transport code, never a verdict on availability; 403 is never absent; genuine absent is 404, 400 (holidays), or 200-with-'Sem comunicações'-body; sync-manifest.parquet is the sole source of truth. Manifest query contracts: frontend needs are declared as .qmd files in web/src/queries/, rendered by scripts/render_queries.py into web/public/data/, with a matching Zod schema + registry entry in web/src/lib/data/contracts.ts. Style: no blind except Exception (BLE001) outside the documented per-item worker-loop bulkhead exception (ADR 0011); TRY300/TRY301/TRY401 enforced; ruff strict; Python 3.12+, from __future__ import annotations. Before committing: ruff check, ruff format --check, pytest -q. Nothing in CLAUDE.md changed relative to what today's prior rounds (r3erpr/aezdb9/yd5lu0/41w39p) recorded."
---

# Leitura de CLAUDE.md

Leitura completa das instruções de projeto. Reconfirma as regras de correção sobre `djen_raw`/`djen_status`/403 nunca-ausente, o `sync-manifest.parquet` como fonte única de verdade, o contrato de queries `.qmd` para o frontend, e as regras de estilo (ruff estrito, TRY300/301/401, sem `except Exception` amplo fora do bulkhead documentado na ADR 0011). Nenhuma divergência das rodadas anteriores do mesmo dia.
