---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-1fxd8b-evidence-green-pure-function"
run_id: "2026-09-05-exciting-mccarthy-1fxd8b"
goal_id: "2026-09-05-exciting-mccarthy-1fxd8b-goal-evidence-matrix"
kind: "test_green"
reference: "web/src/lib/processoCnj.ts — evidenceMatrixRows(), FONTE_PAPEL, EvidenceMatrixRow/EvidenceStatus/Papel types"
summary: "Implemented evidenceMatrixRows(fontes, avisos, cobertura) mapping each of ALL_FONTES to {fonte, papel, status}, with indisponivel (via a matching avisos entry or a cobertura entry with status 'unavailable') taking precedence over presente/ausente. All 7 previously-red tests now pass; full processoCnj.test.ts suite (81 tests) stays green."
---

# GREEN: evidenceMatrixRows

`npx vitest run src/lib/processoCnj.test.ts -t evidenceMatrixRows` → 7 passed, 74 skipped.
