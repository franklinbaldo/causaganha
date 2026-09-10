---
type: AgentReading
id: "2026-09-10-exciting-mccarthy-8042ey-reading-claude-md"
run_id: "2026-09-10-exciting-mccarthy-8042ey"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Read in full via the system-provided project instructions. Two runtime surfaces: Python backend (src/causaganha, src/djen_backup) and web frontend (web/, Astro+Svelte). Correctness rules directly relevant to this round: djen_raw is the raw HTTP transport code, never a verdict on availability; genuine absent is 404, 400 (holidays), or 200-with-'Sem comunicações'-body (no download URL); djen_raw='200' + djen_status='available' is NOT self-consistent proof historically (~79K legacy rows from a body-blind checker); sync-manifest.parquet is the sole source of truth, the legacy sync-manifest.csv is a derived export only. Style rules: no blind except Exception (BLE001) outside the documented per-item worker-loop bulkhead (ADR 0011); TRY300/TRY301/TRY401 enforced; ruff strict; Python 3.12+, from __future__ import annotations. Before committing: ruff check, ruff format --check, pytest -q. Nothing changed relative to what today's prior rounds recorded; this reading independently re-verified the file against the working tree, not just memory of prior rounds' summaries."
---

# Leitura de CLAUDE.md

Leitura completa das instruções de projeto (via system prompt). Reconfirma as regras de correção sobre `djen_raw`/`djen_status`/403-nunca-ausente, o `sync-manifest.parquet` como fonte única de verdade e a regra histórica de que `djen_raw="200"` não é prova de auto-consistência com `djen_status="available"` — regra que motivou o módulo `src/djen_backup/absent_consistency.py` examinado nesta rodada. Regras de estilo (ruff estrito, TRY300/301/401, sem `except Exception` amplo fora do bulkhead da ADR 0011) confirmadas sem divergência.
