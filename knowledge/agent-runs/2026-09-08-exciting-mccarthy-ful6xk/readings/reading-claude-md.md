---
type: AgentReading
id: "2026-09-08-exciting-mccarthy-ful6xk-reading-claude-md"
run_id: "2026-09-08-exciting-mccarthy-ful6xk"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Re-read in full at round start. Correctness rules for djen_backup (djen_raw is a transport code, not a verdict; 403 must never be treated as absent; genuine absent is 404, 400, or 200-with-'Sem comunicações'-body; the historical ~79K legacy-row false-positive issue already resolved by promoting the corrected sync-manifest.parquet) are unchanged since the prior round (2xmp5l, 2026-09-08T01:36Z) and were already the basis of several already-merged fixes today (PR #1287 apply_event downgrade, PR #1297 reset_manifest djen_raw clear). The CSS token boundary section (lines 67-76) was itself corrected by 2xmp5l's PR #1300 to name three (not four) live legacy Svelte islands after TribunalCalendar.svelte was deleted as dead code — verified this correction is present and accurate in the current file. No stale claim found in CLAUDE.md this round; treating it as authoritative and consistent with the live tree."
---

# Leitura de CLAUDE.md

Releitura completa. As regras de correção do djen_backup (204 status é transporte, não veredito; 403 nunca é absent; 200 sem URL de download é absent) seguem vigentes e já orientaram várias correções mescladas hoje. A seção CSS token boundary já está corrigida (rodada 2xmp5l apagou `TribunalCalendar.svelte` e atualizou a contagem de ilhas legadas de quatro para três). Nenhuma inconsistência nova encontrada nesta releitura.
