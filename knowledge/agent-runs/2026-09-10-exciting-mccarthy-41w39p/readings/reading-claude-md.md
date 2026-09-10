---
type: AgentReading
id: "2026-09-10-exciting-mccarthy-41w39p-reading-claude-md"
run_id: "2026-09-10-exciting-mccarthy-41w39p"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Read in full via the system-provided project instructions. Correctness/style rules unchanged from the prior same-day rounds (r3erpr, aezdb9, yd5lu0): djen_raw is the raw HTTP transport code, never a verdict on availability; 403 is never absent; genuine absent is 404, 400 (holidays), or 200-with-'Sem comunicações'-body; sync-manifest.parquet is the sole source of truth. Explicitly documents the periodic IA upload of the manifest ('Periodic IA upload every 10 min protects against crashes' -- Architecture section, djen-backup sync engine) and 3 independent worker pools (checkers/downloaders/uploaders) in src/djen_backup/engine.py. Style: no blind except Exception (BLE001), TRY300/TRY301/TRY401 enforced, Python 3.12+. .claude/hourly-loop.md (checked again, consistent with r3erpr/aezdb9/yd5lu0's prior finding) marks the AgentRun scaffold mechanism as legacy for the Wisk-based hourly loop but this session's own scheduled-task prompt explicitly requests it -- followed the same standing precedent as the last three same-day rounds: use the legacy scaffold for this track, which remains genuinely parallel to (not superseded by) the Wisk lineage."
---

# Leitura de CLAUDE.md

Releitura completa via as instruções de projeto fornecidas pelo sistema. Nenhuma divergência de correção em relação às rodadas anteriores do mesmo dia. Reconfirma o texto sobre o upload periódico do manifest a cada 10 min como "proteção contra crashes" -- relevante para o goal desta rodada.
