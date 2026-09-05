---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-1a1ih8-evidence-ci-astro-build-fix"
run_id: "2026-09-05-exciting-mccarthy-1a1ih8"
goal_id: "2026-09-05-exciting-mccarthy-1a1ih8-goal-publicacoes-search-first-hierarchy"
kind: "ci"
reference: "PR #1160, check_run_id 101371808094 (compare-product-surfaces), run https://github.com/franklinbaldo/causaganha/actions/runs/33990520898/job/101371808094; local reproduction via `npx astro build` with scripts/render_contract_fixture.py fixture data"
summary: "PR #1160's compare-product-surfaces check failed with 'TypeError: Cannot read properties of undefined (reading config)' while Astro's prerender pipeline tried to render a spurious route '/publicacoes/index.order.test', because Astro treats every .ts file under web/src/pages/ (recursively) as a routable endpoint. Reproduced locally: `uv run python scripts/render_contract_fixture.py /tmp/cg-fixture-check` produced a fixture-backed public/data/ (including site-status.json, which /publicacoes's frontmatter requires at build time), copying that into web/public/data/ and running `npx astro build` against the original (un-prefixed) index.order.test.ts also failed while enumerating /publicacoes/*.html routes. After renaming the file to _index.order.test.ts (Astro's own documented underscore-prefix exclusion, confirmed in node_modules/astro/dist/core/routing/create-manifest.js), the same real `npx astro build` command completed cleanly: 109 pages built, no /publicacoes/index.order.test route in dist/, and dist/publicacoes.html still contains both the 'PublicationSearch' island and the 'Cobertura e lacunas' text, confirming the reordered page content survived unaffected. `cd web && npx vitest run src/pages/publicacoes` still passes 3/3 with the renamed file, and `npm run lint` stays clean."
---

# Evidência: causa raiz e correção do CI vermelho em `compare-product-surfaces`

O Astro trata qualquer `.ts` sob `web/src/pages/` como rota, inclusive o teste Vitest desta rodada — quebrando o build real do site (109 páginas). Reproduzido localmente com dados de fixture (`scripts/render_contract_fixture.py`) e corrigido renomeando para `_index.order.test.ts` (mecanismo oficial do próprio Astro). `npx astro build` real passa limpo após a correção; `vitest`/`lint` continuam verdes.
