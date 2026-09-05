---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-e9r0mj-evidence-green-mapping-parity"
run_id: "2026-09-05-exciting-mccarthy-e9r0mj"
goal_id: "2026-09-05-exciting-mccarthy-e9r0mj-goal-datajud-temporal-authority"
kind: "test_green"
reference: "web/src/lib/processoQueryPlanParity.test.ts (mapping-layer parity test); scripts/processo_query_plan_compare.py (_python_mapped, run_cases)"
summary: "With the toIsoTimestamp() fix restored, ran `npx vitest run src/lib/processoQueryPlanParity.test.ts src/lib/processoCnj.test.ts`: 87/87 passed, including the reintroduced mapping-layer parity test's 8 cases (PRESENT/ABSENT x DJEN/JURIS/STJ/DataJud), each comparing the real Python _build_* mapper output against the real Web map*Row output for the shared query_plan_fixtures.py fixture. This satisfies #1107's acceptance criteria for the mapping boundary: dates/nulls/lists agree after normalization, and DataJud's genuine TIMESTAMP field no longer diverges in either value or format between runtimes."
---

# GREEN: paridade de mapeamento restaurada

Com a correção aplicada, a prova de paridade de mapeamento reintroduzida passa integralmente para as 4 fontes, presente e ausente.
