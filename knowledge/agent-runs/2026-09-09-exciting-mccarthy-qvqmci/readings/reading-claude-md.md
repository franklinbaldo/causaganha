---
type: AgentReading
id: "2026-09-09-exciting-mccarthy-qvqmci-reading-claude-md"
run_id: "2026-09-09-exciting-mccarthy-qvqmci"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Full re-read at round start. Core invariants unchanged from the immediately preceding rounds' readings: djen_raw is a transport code only, never a verdict (a 200 can still be genuinely absent when the body is 'Sem comunicações' with no download URL); 403 must never be treated as absent (CloudFront/WAF rate-limiting); genuine absent is 404, 400, or 200-without-URL. The historical ~79K legacy-row false-positive issue is resolved (sync-manifest.parquet promoted to sole source of truth, sync-manifest.csv retired as canonical, never re-read). CSS token boundary section still names exactly three live legacy Svelte islands (ProcessoLookup, PublicationSearch, SavedConsultations) needing --papel-*/--s-* aliases; Panda's include only scans .astro/.js/.ts/.tsx, never .svelte -- confirmed still true, no new bespoke css() calls added to a .svelte file since the last check. Style rules unchanged: ruff strict, no blind except Exception (ADR-0011 carves out per-item worker-pool bulkheads only), TRY300/TRY301/TRY401 enforced. File map (engine.py/manifest.py/djen.py/archive.py/retry.py, scripts/render_queries.py, web/src/queries/*.qmd) matches current repo layout including scripts/reconcile_processos.py and scripts/pipeline/export_ratings.py, both referenced by the last three merged rounds' fixes. No stale claim found this round; no update to CLAUDE.md needed."
---

# Leitura de CLAUDE.md

Releitura completa no início da rodada. Nenhuma regra desatualizada encontrada; as seções sobre djen_backup, contratos de query e fronteira Panda/CSS continuam batendo com o estado real do repositório.
