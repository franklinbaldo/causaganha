---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-1a1ih8-check-astro-build-real"
run_id: "2026-09-05-exciting-mccarthy-1a1ih8"
goal_id: "2026-09-05-exciting-mccarthy-1a1ih8-goal-publicacoes-search-first-hierarchy"
command: "uv run python scripts/render_contract_fixture.py /tmp/cg-fixture-check && cp -r /tmp/cg-fixture-check/web/public/data/* web/public/data/ && cd web && npx astro build"
result: "passed"
evidence_id: "2026-09-05-exciting-mccarthy-1a1ih8-evidence-ci-astro-build-fix"
summary: "Real astro build (not the offline structural test) run locally with fixture data standing in for site-status.json: failed against the original index.order.test.ts (same TypeError CI hit), passed after renaming to _index.order.test.ts — 109 pages built, no spurious route, dist/publicacoes.html carries both PublicationSearch and Cobertura e lacunas markers. Fixture data (gitignored web/public/data/*.json) and dist/ output removed after validation; an unrelated regenerated public/og/tjro.svg (an OG image derived from the injected fixture numbers) was reverted with git checkout."
---

# Check: build real do Astro após a correção

`npx astro build` real (com dados de fixture) falha contra o arquivo original e passa após o rename para `_index.order.test.ts` — 109 páginas, sem rota espúria.
