---
type: AgentReading
id: "2026-09-09-exciting-mccarthy-ko7vqq-reading-claude-md"
run_id: "2026-09-09-exciting-mccarthy-ko7vqq"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Full re-read at round start; content unchanged since a4a5bbf (2026-09-08), same state confirmed by every round today (pf1xhn through nnysz7). Core invariants restated for this round's own use: djen_raw is a transport code only, never a verdict on availability -- genuine absent is 404, 400, or 200-without-download-URL ('Sem comunicações'); 403/5xx/timeout/network are transient, never absent. sync-manifest.parquet is the sole source of truth. Engine runs 3 independent worker pools (checkers/downloaders/uploaders); per-item lock + token bucket for IA uploads; ia_s3._perform_upload must read_bytes(), never open('rb'). Manifest query contracts: new frontend datasets go through .qmd files in web/src/queries/ plus a Zod schema/registry entry in web/src/lib/data/contracts.ts. CSS token boundary: Panda via the cobogo preset for all substantive pages; three legacy Svelte islands (ProcessoLookup, PublicationSearch, SavedConsultations) keep --papel-*/--s-* aliases; Panda's include never scans .svelte, so new Svelte styling stays in scoped <style> blocks, not css(). Style: ruff strict, no blind except Exception outside the ADR-0011 per-item worker-pool bulkhead carve-out, TRY300/TRY301/TRY401 enforced, Python 3.12+ with `from __future__ import annotations`. File map matches current layout (src/djen_backup/{engine,manifest,djen,archive,retry,__main__}.py; scripts/render_queries.py; web/src/queries/*.qmd). No stale claim found; no update needed."
---

# Leitura de CLAUDE.md

Releitura completa no início da rodada. Nenhuma regra desatualizada encontrada; arquivo inalterado desde a4a5bbf, mesmo estado confirmado pelas rodadas anteriores de hoje.
