---
type: AgentReading
id: "2026-09-08-exciting-mccarthy-k18r9l-reading-claude-md"
run_id: "2026-09-08-exciting-mccarthy-k18r9l"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Read in full at round start. Core invariants reconfirmed: sync-manifest.parquet is the sole source of truth (compacted from append-only manifest-log/*.csv by scripts/render_manifest_parquet.py); djen_raw is a bare HTTP transport code (never a verdict) -- availability requires HTTP 200 AND a download URL in the body, a bare 200-without-URL ('Sem comunicacoes') is absent exactly like 404/400; 403 must never be treated as absent (CloudFront/WAF rate-limiting); the retired sync-manifest.csv's ~79K legacy rows conflating bare-200 with available were never backfilled and nothing reads that CSV as canonical anymore. Manifest query contracts (.qmd under web/src/queries/) are the only sanctioned path for new frontend datasets: add .qmd + Zod schema/registry entry in web/src/lib/data/contracts.ts + loadContract(). CSS: one design system (Panda via cobogo preset); web/src/index.css is a compatibility bridge for exactly three legacy Svelte islands (ProcessoLookup, PublicationSearch, SavedConsultations) -- no new bespoke custom properties anywhere else. Style: ruff strict, no blind except Exception (BLE001), TRY300/301/401 enforced, Python 3.12+ with `from __future__ import annotations`. No divergence found between this document and the current codebase state beyond the already-known, already-logged except-Exception/BLE001 architectural gap (see prior rounds b4t8pv/1c7t6u) which needs a human policy decision, not a mechanical fix."
---

# Reading: CLAUDE.md

Releitura completa no início da rodada. Nenhuma divergência nova entre o documento e o estado atual do código, além do gap já conhecido de `except Exception`/BLE001 (decisão arquitetural pendente, não selecionável mecanicamente).
