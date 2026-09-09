---
type: AgentReading
id: "2026-09-09-exciting-mccarthy-8esdwh-reading-claude-md"
run_id: "2026-09-09-exciting-mccarthy-8esdwh"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Read in full at round start. Correctness rules for djen_backup unchanged since the last several rounds in this family: djen_raw is a transport code, never a verdict on availability; a bare 200 is not 'available' (must also have a download URL, else it's 'Sem comunicações' == absent, same as 404/400); 403 must never be treated as absent (WAF/CloudFront rate-limiting); the ~79K legacy false-positive rows were already resolved by promoting sync-manifest.parquet as the sole source of truth (legacy sync-manifest.csv retired). CSS token boundary section still names exactly three live legacy Svelte islands (ProcessoLookup, PublicationSearch, SavedConsultations) styling via --papel-*/--s-* aliases; new work should use Panda css()/recipes. Ruff strict, TRY300/TRY301/TRY401 enforced, no blind except Exception outside the documented per-item worker-pool bulkhead pattern (ADR-0011). File map (engine.py/manifest.py/djen.py/archive.py/retry.py/__main__.py, scripts/render_queries.py) matches the current tree. No drift detected between CLAUDE.md and the current codebase in this pass."
---

# Leitura de CLAUDE.md

Releitura completa no início da rodada. Nenhuma divergência encontrada entre as regras documentadas e o estado atual do código.
