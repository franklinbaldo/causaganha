---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-1fxd8b-evidence-red-pure-function"
run_id: "2026-09-05-exciting-mccarthy-1fxd8b"
goal_id: "2026-09-05-exciting-mccarthy-1fxd8b-goal-evidence-matrix"
kind: "test_red"
reference: "web/src/lib/processoCnj.test.ts — describe('evidenceMatrixRows', ...) (7 tests)"
summary: "Added 7 tests for a not-yet-existing evidenceMatrixRows() pure function before writing it. All 7 failed with 'evidenceMatrixRows is not a function', confirming the tests exercise real not-yet-built behavior: presente/ausente classification, indisponivel precedence via avisos, indisponivel precedence via cobertura status, an unrelated healthy cobertura entry not tainting another fonte, row count/order matching ALL_FONTES, and the papel mapping."
---

# RED: evidenceMatrixRows

`npx vitest run src/lib/processoCnj.test.ts -t evidenceMatrixRows` → 7 failed, 74 skipped.
