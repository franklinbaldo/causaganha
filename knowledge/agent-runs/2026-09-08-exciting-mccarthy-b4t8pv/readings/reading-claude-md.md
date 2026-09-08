---
type: AgentReading
id: "2026-09-08-exciting-mccarthy-b4t8pv-reading-claude-md"
run_id: "2026-09-08-exciting-mccarthy-b4t8pv"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Read in full at round start. Key facts reconfirmed: sync-manifest.parquet on IA is the sole source of truth (append-only manifest-log/*.csv compacted by scripts/render_manifest_parquet.py); djen_raw is a bare HTTP transport code, never a verdict -- availability requires HTTP 200 AND a download URL in the body, since a 200-without-URL is absent exactly like 404 or 400; 403 must never be treated as absent (CloudFront/WAF rate-limiting); ~79K legacy rows in the retired sync-manifest.csv conflated bare-200 with available and were never backfilled, so any available/absent discrepancy found elsewhere must be verified against live DJEN before 'fixing'. Manifest query contracts: .qmd files under web/src/queries/ only ever see the manifest view via DuckDB -- no access to Python config. CSS: one design system (Panda via the cobogo preset); web/src/index.css is a compatibility bridge for exactly three legacy Svelte islands (ProcessoLookup, PublicationSearch, SavedConsultations) only -- no new bespoke custom properties. Style: ruff strict, 'No blind except Exception' stated as a rule though not caught by ruff's BLE001 when the handler calls .exception(...) (a gap the immediately prior round, 1c7t6u, already flagged and left unselected as a policy question). Python 3.12+, TRY300/301/401 enforced. This matches recent git log entries (backfill_probe body-vs-status classification, absent/unknown double-counting fixes, business-day-vs-calendar-day scaling) -- the CLAUDE.md correctness rules are being actively enforced by recent rounds, not just documentation debt."
---

# Reading: CLAUDE.md

Releitura completa no início da rodada. Regras de correção do djen_backup e do limite de tokens CSS reconfirmadas e vigentes; nenhuma divergência nova encontrada entre o documento e o estado atual do código além do gap já conhecido de `except Exception`/BLE001 (não selecionado nas últimas rodadas por exigir decisão arquitetural prévia).
