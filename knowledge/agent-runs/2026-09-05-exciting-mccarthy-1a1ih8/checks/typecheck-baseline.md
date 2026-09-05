---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-1a1ih8-check-typecheck-baseline"
run_id: "2026-09-05-exciting-mccarthy-1a1ih8"
goal_id: "2026-09-05-exciting-mccarthy-1a1ih8-goal-publicacoes-search-first-hierarchy"
command: "cd web && npm run typecheck, once on this branch's diff and once with the diff stashed via `git stash -u` (excluding the codegen-regenerated djen-zod.gen.ts noise from pretypecheck), to isolate this round's contribution to the astro-check error count"
result: "passed"
evidence_id: "2026-09-05-exciting-mccarthy-1a1ih8-evidence-green-publicacoes-order"
summary: "Both runs report identically 19 errors/0 warnings/3 hints (all in pre-existing testing-library RenderResult typing idioms and the pre-existing renderedContracts.integration.test.ts, none touching web/src/pages/publicacoes/**) — this round's change contributes zero new typecheck errors."
---

# Check: baseline de typecheck inalterado

`npm run typecheck`: 19/0/3 igual antes (via `git stash -u`) e depois do diff — nenhum erro novo introduzido por este round.
