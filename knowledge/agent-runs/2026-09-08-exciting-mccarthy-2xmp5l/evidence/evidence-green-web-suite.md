---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-2xmp5l-evidence-green-web-suite"
run_id: "2026-09-08-exciting-mccarthy-2xmp5l"
goal_id: "2026-09-08-exciting-mccarthy-2xmp5l-goal-delete-tribunal-calendar"
kind: "test_green"
reference: "npx vitest run (web/); npm run lint; npm run typecheck"
summary: "After `git rm web/src/components/TribunalCalendar.svelte` and the CLAUDE.md edit: `npx vitest run` — 65 test files, 491 tests, all passed (identical counts to pre-deletion, confirming no test depended on the removed component). `npm run lint` (eslint) — 0 errors (43 pre-existing generated-file warnings). `npm run typecheck` (astro check) — 0 errors, 0 warnings, 5 pre-existing hints. web/src/lib/djen-zod.gen.ts's prebuild-regenerated orval-version drift (unrelated to this change, already diagnosed by the prior round) was discarded via `git checkout --` to keep the diff scoped."
---

# Evidência GREEN

```
Test Files  65 passed (65)
     Tests  491 passed (491)
```

`eslint .`: 0 errors. `astro check`: 0 errors, 0 warnings, 5 hints pré-existentes. Mesma contagem de testes de antes da exclusão — nenhum teste dependia do componente removido.
