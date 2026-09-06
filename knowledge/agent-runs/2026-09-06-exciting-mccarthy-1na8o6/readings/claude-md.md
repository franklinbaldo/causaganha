---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-1na8o6-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-1na8o6"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Two runtime surfaces documented (djen-backup sync engine in src/djen_backup, web frontend in web/ Astro 5 + Svelte 5). This round's selected work is web-only — a bugfix inside web/src/components/SavedConsultations.svelte plus its Vitest suite — so djen_backup's DJEN-status/manifest correctness rules and the .qmd query-contract section do not apply. The CSS token boundary section is directly relevant only in that SavedConsultations.svelte is not one of the four legacy Svelte islands (ProcessoLookup, PublicationSearch, SavedConsultations IS actually one of the four listed) — re-checked: SavedConsultations.svelte IS one of the four legacy islands named in CLAUDE.md, so the correct rule is 'fine to keep using its existing --papel-*/--s-* names; don't introduce new ones' — the new 'Marcar como visto' button reuses the exact existing `outline secondary` class already used by the same component's Renomear/Remover buttons, introducing no new custom property. 'Before committing' gates apply: ruff check/format/pytest -q (unaffected, no Python touched) and web's own gates (npm run lint, npm run typecheck, npm run test) since production .svelte/.test.ts files changed."
---

# Leitura de CLAUDE.md

`SavedConsultations.svelte` é um dos quatro componentes Svelte legados listados na seção "CSS token boundary" — a regra correta para ele é reaproveitar as classes/tokens já existentes (`outline secondary`, usada por Renomear/Remover) em vez de inventar uma custom property nova. O trabalho desta rodada não toca `djen_backup` nem `.qmd`, então as regras de `djen_raw`/`sync-manifest` não se aplicam. Gates: `npm run lint`/`typecheck`/`test` no `web/` (nenhum Python foi alterado, mas `ruff`/`pytest` foram rodados mesmo assim para confirmar ausência de regressão).
