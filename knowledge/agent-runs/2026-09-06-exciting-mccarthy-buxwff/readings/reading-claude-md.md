---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-buxwff-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-buxwff"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "This round's work is web-only (web/src/layouts/Layout.astro, web/src/pages/index.astro) and touches neither djen_backup's manifest/DJEN-status rules nor any .qmd query contract, so those correctness rules do not apply. The CSS token boundary section governs the styling approach: index.astro and Layout.astro are both .astro files (not one of the four legacy Svelte islands), so new markup must style through css()/styled-system recipes reading Panda tokens directly (button, navLink), never a bespoke custom property outside panda.config.ts — confirmed by inspecting node_modules/cobogo/preset/index.mjs for the button recipe's actual variant CSS before choosing a visual. 'Before committing' gates apply: ruff check/format and pytest -q (repo-wide, even though no Python file changed, since CLAUDE.md gates the whole repo) and web's own gates (npm run lint, npm run typecheck, npm run test)."
---

# Leitura de CLAUDE.md

Trabalho desta rodada é só web (`Layout.astro` + `index.astro`), sem tocar `djen_backup` ou contratos `.qmd`. A fronteira de tokens CSS exige `css()`/recipes do preset `cobogo` (não custom properties novas) — inspecionei `node_modules/cobogo/preset/index.mjs` para confirmar as cores reais de cada variante do recipe `button` antes de escolher qual usar sobre o hero escuro. Gates: `ruff check`/`format`/`pytest -q` (repo todo) e `npm run lint`/`typecheck`/`test` (web).
