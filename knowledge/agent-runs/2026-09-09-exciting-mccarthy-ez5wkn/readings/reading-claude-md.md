---
type: AgentReading
id: "2026-09-09-exciting-mccarthy-ez5wkn-reading-claude-md"
run_id: "2026-09-09-exciting-mccarthy-ez5wkn"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Full re-read at round start; unchanged since a4a5bbf (2026-09-08), already confirmed current by the immediately preceding round (qvqmci). Core invariants: djen_raw is a transport code only, never a verdict on availability -- genuine absent is 404, 400, or 200-without-download-URL ('Sem comunicações'); 403/5xx/timeout/network are transient, never absent. sync-manifest.parquet is the sole source of truth (sync-manifest.csv retired). Engine runs 3 independent worker pools (checkers/downloaders/uploaders); per-item lock + token bucket for IA uploads. CSS token boundary: Panda via the cobogo preset for all substantive pages; three legacy Svelte islands (ProcessoLookup, PublicationSearch, SavedConsultations) keep --papel-*/--s-* aliases, Panda's include never scans .svelte. Style: ruff strict, no blind except Exception outside the ADR-0011 per-item worker-pool bulkhead carve-out, TRY300/TRY301/TRY401 enforced. File map matches current layout (engine.py/manifest.py/djen.py/archive.py/retry.py under src/djen_backup/, scripts/render_queries.py, web/src/queries/*.qmd). No stale claim found; no update needed."
---

# Leitura de CLAUDE.md

Releitura completa no início da rodada. Confirma o que a rodada anterior (qvqmci) já havia verificado: nenhuma regra desatualizada, arquivo inalterado desde a4a5bbf.
