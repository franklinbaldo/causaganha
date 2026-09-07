---
type: AgentCheck
id: "2026-09-07-exciting-mccarthy-14x3v7-check-web-suite"
run_id: "2026-09-07-exciting-mccarthy-14x3v7"
goal_id: "2026-09-07-exciting-mccarthy-14x3v7-goal-djen-retry-after-floor"
command: "npm ci && npx vitest run && npm run lint && npm run typecheck (all in web/)"
result: "passed"
summary: "vitest: 65 test files, 491 tests, all passed (including the new RED-then-GREEN retry-after test). eslint: 0 errors (43 pre-existing generated-file warnings, unrelated). astro check: 0 errors, 0 warnings, 5 pre-existing hints, unrelated."
evidence_id: "2026-09-07-exciting-mccarthy-14x3v7-evidence-green-retry-after"
---

# Check: suite web completa

Rodada após aplicar o fix em `djenClient.ts`. `npm run typecheck` regenerou `web/src/lib/djen-zod.gen.ts` com diffs de uma versão diferente do `orval` instalado neste ambiente (comentário de versão + `zod.number()` → `zod.int()`) — descartado via `git checkout --` por ser drift de codegen não relacionado a este fix, não incorporado ao commit.
