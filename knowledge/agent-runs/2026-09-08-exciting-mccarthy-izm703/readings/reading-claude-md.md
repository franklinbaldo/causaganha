---
type: AgentReading
id: "2026-09-08-exciting-mccarthy-izm703-reading-claude-md"
run_id: "2026-09-08-exciting-mccarthy-izm703"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Re-read in full at round start. Correctness rules for djen_backup unchanged since the last read in this family (obl3ux, 2026-09-08T07:26Z): djen_raw is a transport code not a verdict; 403 must never be treated as absent; genuine absent is 404, 400, or 200-with-'Sem comunicações'-body; the historical ~79K legacy-row issue is resolved via the promoted sync-manifest.parquet as sole source of truth. The CSS token boundary section still correctly names three live legacy Svelte islands (ProcessoLookup, PublicationSearch, SavedConsultations) -- TribunalCalendar.svelte, deleted two rounds ago, is not mentioned. No stale claim found against the current repo state (git log confirms this file's own content matches HEAD at 2e2f324). Since obl3ux's close (PR #1313, merged), main advanced substantially via two separate tracking families: this repo's own djen_backup/manifest track (PRs #1319 docs Astro-version fix, #1323 downgrade absent+empty-djen_raw rows to unknown in the compactor, #1325 extract shared absent self-consistency rule into a tested module) and a parallel 'Wisk-loop' family (PRs #1305 DJENRateLimitedError in drain worker, #1307 remove abandoned dashboard-fetch architecture, #1309 delete orphaned TribunalCoverageGrid.astro, #1311 rewrite FRONTEND.md's Pico CSS section for Panda CSS) -- none of these touch CLAUDE.md's own content, so its accuracy claim stands unaffected."
---

# Leitura de CLAUDE.md

Releitura completa no início da rodada. Regras de correção do djen_backup (djen_raw como código de transporte, nunca veredito; 403 nunca é ausência; ausência genuína é 404/400/200-sem-URL; manifest.parquet como fonte única) seguem vigentes e sem novidade desde a última leitura desta família (`obl3ux`). Seção CSS token boundary segue correta (três ilhas legadas vivas). Desde o fechamento de `obl3ux` (PR #1313), a `main` avançou por duas famílias paralelas: a própria (PRs #1319, #1323, #1325, sobre o manifesto e docs) e a "Wisk-loop" (PRs #1305, #1307, #1309, #1311). Nenhuma altera o conteúdo do CLAUDE.md.
