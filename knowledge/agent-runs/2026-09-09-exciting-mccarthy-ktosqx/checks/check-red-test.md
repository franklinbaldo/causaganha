---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-ktosqx-check-red-test"
run_id: "2026-09-09-exciting-mccarthy-ktosqx"
command: "npx vitest run src/components/DateDetail.pagination.test.ts (web/, against unmodified DateDetail.svelte)"
result: "failed"
summary: "1 test failed: could not find '35 pág.' text; DOM showed '30 pág.' and 'Página 2 de 30' instead, confirming the hardcoded 30-probe cap. See evidence-red-test."
---

# Check: teste RED

Rodado contra o componente original, antes da correção. Falhou exatamente como esperado -- ver evidence-red-test.
