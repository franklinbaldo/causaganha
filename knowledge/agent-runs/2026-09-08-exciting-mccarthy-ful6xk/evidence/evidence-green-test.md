---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-ful6xk-evidence-green-test"
run_id: "2026-09-08-exciting-mccarthy-ful6xk"
goal_id: "2026-09-08-exciting-mccarthy-ful6xk-goal-fix-tribunal-completion-formula"
kind: "test_green"
reference: "web/src/lib/coverageInsights.ts line 171-173 fix; `npx vitest run src/lib/coverageInsights.test.ts` after the fix"
summary: "Changed `completion = coverageSize / expectedDays * 100` to `completion = (coverageSize + absentCount) / expectedDays * 100`. Both new tests pass: 2 passed (2), 0 failed. Full web suite re-run afterwards: 66 test files, 493 tests, all green (up from 65 files/491 tests at round start, matching the one new test file added)."
---

# Evidência GREEN

Correção de uma linha: somar `absentCount` ao numerador. Os dois testes novos passam, e a suíte completa do frontend (66 arquivos, 493 testes) permanece verde.
