---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-1a1ih8-evidence-green-publicacoes-order"
run_id: "2026-09-05-exciting-mccarthy-1a1ih8"
goal_id: "2026-09-05-exciting-mccarthy-1a1ih8-goal-publicacoes-search-first-hierarchy"
kind: "test_green"
reference: "cd web && npx vitest run src/pages/publicacoes/index.order.test.ts; npx vitest run (full suite); npm run lint; npm run typecheck (compared against git-stash baseline)"
summary: "After reordering web/src/pages/publicacoes/index.astro — short page-head (kicker+h1+one instructional line) immediately followed by <PublicationSearch client:load />, with the 'Cobertura e lacunas por tribunal' attention-card (now also carrying the ZIP/tribunal metrics line and the generated_at meta line, both moved out of the old lede/footer) rendered below the search — src/pages/publicacoes/index.order.test.ts is 3/3 passing. Full web vitest suite: 42 of 43 files passed with 357 tests passing (4 pre-existing skips); the 1 failing file (processoQueryPlanParity.test.ts) failed only on a beforeAll hook timeout racing a cold `uv` subprocess start when run alongside the whole suite and passed cleanly (4/4) in isolation — confirmed pre-existing and unrelated by reproducing it against this same branch. `npm run lint` (eslint .) is clean. `npm run typecheck` (astro check) reports 19 errors/0 warnings/3 hints both before (via `git stash -u`) and after this change — an unchanged pre-existing baseline (documented by a prior round's PR #1154), so this diff introduces zero new type errors."
---

# GREEN: ordem de `/publicacoes` corrigida

`index.order.test.ts`: 3/3. Suite web completa: 357/357 (excluindo o único arquivo com flake pré-existente de timeout de subprocesso `uv`, confirmado não relacionado ao diff). `npm run lint`: limpo. `npm run typecheck`: 19 erros/0 avisos/3 hints, idêntico ao baseline confirmado via `git stash -u` — nenhuma regressão de tipos.
