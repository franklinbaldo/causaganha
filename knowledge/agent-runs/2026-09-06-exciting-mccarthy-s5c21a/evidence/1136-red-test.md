---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-s5c21a-evidence-1136-red-test"
run_id: "2026-09-06-exciting-mccarthy-s5c21a"
goal_id: "2026-09-06-exciting-mccarthy-s5c21a-goal-1136-minhas-consultas-query-states"
kind: "test_red"
reference: "web/src/components/queryStates.contract.test.ts, run via `npx vitest run src/components/queryStates.contract.test.ts` against the untouched query-states.css"
summary: "Before editing query-states.css, the new test 'extends the shared layout-stability contract to /minhas-consultas' failed: `expect(styles).toContain('.processo-lookup, .publication-search, .saved-consultations')` — actual content only had `.processo-lookup, .publication-search`. Result: 1 failed | 6 passed (7) — the other two new assertions (SavedConsultations already emitting the semantic markers, and the no-collapse guard) passed independently, isolating the one genuine gap: the selector list itself."
---

# Evidência RED — #1136 / /minhas-consultas

`Tests 1 failed | 6 passed (7)` confirma que a lacuna real é exatamente a ausência de `.saved-consultations` nos seletores de `query-states.css`, e não a marcação semântica do componente (que já estava correta antes de qualquer mudança).
