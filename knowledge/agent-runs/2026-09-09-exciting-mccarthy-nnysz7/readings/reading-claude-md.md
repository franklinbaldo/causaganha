---
type: AgentReading
id: "2026-09-09-exciting-mccarthy-nnysz7-reading-claude-md"
run_id: "2026-09-09-exciting-mccarthy-nnysz7"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Full re-read at round start; content unchanged since a4a5bbf (2026-09-08), already confirmed current by the immediately preceding rounds today (pf1xhn, p7xocl, ez5wkn among them). Core invariants restated for this round's own use: djen_raw is a transport code only, never a verdict on availability -- genuine absent is 404, 400, or 200-without-download-URL ('Sem comunicações'); 403/5xx/timeout/network are transient, never absent. sync-manifest.parquet is the sole source of truth (sync-manifest.csv retired as canonical, still producible as a derived export). Engine runs 3 independent worker pools (checkers/downloaders/uploaders); per-item lock + token bucket for IA uploads; ia_s3._perform_upload must read_bytes(), never open('rb'). CSS token boundary: Panda via the cobogo preset for all substantive pages; three legacy Svelte islands (ProcessoLookup, PublicationSearch, SavedConsultations) keep --papel-*/--s-* aliases, Panda's include never scans .svelte. Style: ruff strict, no blind except Exception outside the ADR-0011 per-item worker-pool bulkhead carve-out, TRY300/TRY301/TRY401 enforced, Python 3.12+ with `from __future__ import annotations`. File map matches current layout. No stale claim found; no update needed."
---

# Leitura de CLAUDE.md

Releitura completa no início da rodada. Nenhuma regra desatualizada encontrada; arquivo inalterado desde a4a5bbf, mesmo estado confirmado pelas rodadas anteriores de hoje.
