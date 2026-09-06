---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-488tov-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-488tov"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces: Python backend (src/causaganha, src/djen_backup) and web frontend (web/, Astro 5 + Svelte 5). This round's selected work is web-only, entirely inside web/src/lib and web/src/components — no djen_backup sync-manifest/djen_raw/djen_status rules apply, and no .qmd query contract is touched. The CSS token boundary section is directly relevant: SavedConsultations.svelte is one of the four legacy Svelte islands named in CLAUDE.md (ProcessoLookup, PublicationSearch, SavedConsultations, TribunalCalendar) that predate the Panda/Cobogó reboot — the rule for it is to keep reusing its existing --papel-*/--s-* names and scoped <style> block, never introduce css()/new custom properties. New buttons for export/import should reuse the exact `outline secondary` class already used by the same component's Renomear/Remover buttons. Before-committing gates apply in full: ruff check/format + pytest -q (unaffected unless Python is touched, run anyway to prove no regression) and web's own gates (npm run lint, npm run typecheck, npm run test) since production .svelte/.ts/.test.ts files change."
---

# Leitura de CLAUDE.md

`SavedConsultations.svelte` é um dos quatro componentes Svelte legados da seção "CSS token boundary" — reaproveitar `outline secondary` e os tokens `--s-*`/`--papel-*` já existentes, sem introduzir `css()` ou custom properties novas. O trabalho é 100% `web/`, não toca `djen_backup` nem `.qmd`. Gates: `npm run lint`/`typecheck`/`test` em `web/`, e `ruff check`/`ruff format --check`/`pytest -q` no Python para confirmar ausência de regressão.
