---
type: AgentReading
id: "2026-09-09-exciting-mccarthy-ktosqx-reading-claude-md"
run_id: "2026-09-09-exciting-mccarthy-ktosqx"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Full read at round start. Content matches the version every round today has already confirmed current (unchanged since a4a5bbf, 2026-09-08). Core invariants restated for this round's own use: djen_raw is a transport code only, never a verdict on availability -- genuine absent is HTTP 404, 400, or 200-without-download-URL ('Sem comunicações'); 403/5xx/timeout/network are transient, never absent. sync-manifest.parquet on IA is the sole source of truth; sync-manifest.csv is retired as canonical but still producible as a derived export via MANIFEST_COMPACT_WRITEBACK=1. Engine runs 3 independent worker pools (checkers/downloaders/uploaders); per-item lock + token bucket for IA uploads; ia_s3._perform_upload must use file_path.read_bytes(), never file_path.open('rb'). CSS token boundary: Panda via the cobogo preset for all substantive pages; three legacy Svelte islands (ProcessoLookup, PublicationSearch, SavedConsultations) keep --papel-*/--s-* aliases since Panda's include never scans .svelte. Style: ruff strict, no blind except Exception outside the ADR-0011 per-item worker-pool bulkhead carve-out, TRY300/TRY301/TRY401 enforced, Python 3.12+ with `from __future__ import annotations`. File map matches current layout (src/djen_backup/{engine,manifest,djen,archive,retry}.py, scripts/render_queries.py, web/src/queries/*.qmd). No stale claim found; no update needed."
---

# Leitura de CLAUDE.md

Releitura completa no início da rodada. Nenhuma regra desatualizada encontrada; arquivo inalterado desde a4a5bbf, mesmo estado já confirmado pelas rodadas anteriores de hoje.
