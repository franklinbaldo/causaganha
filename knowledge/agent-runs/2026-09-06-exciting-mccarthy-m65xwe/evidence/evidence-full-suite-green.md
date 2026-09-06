---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-m65xwe-evidence-full-suite-green"
run_id: "2026-09-06-exciting-mccarthy-m65xwe"
goal_id: "2026-09-06-exciting-mccarthy-m65xwe-goal-typecheck-debt-and-ci-gate"
kind: "test_green"
reference: "web/ $ npm test; npm run lint; npm run build — all run after the fix, on the scoped diff (unrelated djen-zod.gen.ts regeneration reverted)"
summary: "npm test (vitest): 55 test files, 435 tests, all passed, no assertion changed. npm run lint (eslint): 0 errors, 43 pre-existing warnings confined to generated styled-system/ files (unrelated to this diff). npm run build (astro build, with the same CI-style stub JSON files under public/data/ that .github/workflows/test.yml's web job generates): 109 pages built, 'Complete!', no error. Python side: `uv run ruff check` — all checks passed; `uv run ruff format --check` — 378 files already formatted (no Python file touched by this round's diff anyway)."
---

# GREEN: suíte completa sem regressão

vitest 435/435, eslint 0 erros, astro build completo, ruff limpo — nada regrediu com a correção de tipagem.
