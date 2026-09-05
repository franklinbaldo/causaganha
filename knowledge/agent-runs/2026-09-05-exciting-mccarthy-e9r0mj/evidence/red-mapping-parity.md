---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-e9r0mj-evidence-red-mapping-parity"
run_id: "2026-09-05-exciting-mccarthy-e9r0mj"
goal_id: "2026-09-05-exciting-mccarthy-e9r0mj-goal-datajud-temporal-authority"
kind: "test_red"
reference: "web/src/lib/processoQueryPlanParity.test.ts, it('per-source mapped domain views agree between Python service and Web SQL, present and absent'); scripts/processo_query_plan_compare.py's new _python_mapped()"
summary: "Reintroduced PR #1125's mapping-layer parity test (reusing its diff verbatim) and temporarily reverted mapDatajudRow's ultima_atualizacao back to toIsoDate() to confirm the test still catches the exact drift it was designed for. Ran `npx vitest run src/lib/processoQueryPlanParity.test.ts`: FAILED with 'datajud: mapped view diverges from Python (present case): ... ultimaAtualizacao: Expected \"2024-06-01\", Received \"2024-06-01T00:00:00\"' — reproducing, at the mapping-parity level, the exact drift #1125 originally found. Immediately restored the toIsoTimestamp() fix afterward (no drift left in the working tree)."
---

# RED: paridade de mapeamento reintroduzida ainda detecta o drift

Confirma que a prova de paridade reintroduzida (idêntica à da PR #1125) realmente teria pego o bug original, antes de qualquer correção — não é um teste que passa por acidente.
