---
type: AgentReading
id: "2026-09-09-exciting-mccarthy-0lpi0s-reading-claude-md"
run_id: "2026-09-09-exciting-mccarthy-0lpi0s"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Full re-read at round start. djen_backup correctness rules (djen_raw as transport code only, never a verdict; 403 must never be treated as absent; genuine absent is 404, 400, or 200-with-'Sem comunicações'-body; the historical ~79K legacy-row false-positive already resolved via the promoted sync-manifest.parquet) are unchanged since the last several rounds' readings. CSS token boundary section still correctly names exactly three live legacy Svelte islands (ProcessoLookup, PublicationSearch, SavedConsultations). Manifest query contracts section (.qmd -> contracts.ts -> loadContract) matches the actual shape of scripts/render_queries.py and web/src/lib/data/contracts.ts as directly inspected this round. No stale claim found; no update needed to CLAUDE.md itself this round."
---

# Leitura de CLAUDE.md

Releitura completa. Nenhuma regra desatualizada encontrada. As seções sobre djen_backup, contratos de query e fronteira Panda/CSS seguem batendo com o estado real do código inspecionado nesta rodada (scripts/render_queries.py, scripts/reconcile_processos.py).
