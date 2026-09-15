---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-rt6d4o-evidence-red-test"
run_id: "2026-09-15-exciting-mccarthy-rt6d4o"
goal_id: "2026-09-15-exciting-mccarthy-rt6d4o-goal-direct-equality-processo-cnj"
kind: "test_red"
reference: "web/src/lib/processoCnj.test.ts (novos describe blocks: 'resolveDjenEqualityMode', novos casos em 'SQL builders...' e 'buscarProcesso')"
summary: "npx vitest run src/lib/processoCnj.test.ts com os testes novos adicionados e a implementação ainda não escrita: 10 falhas -- 'resolveDjenEqualityMode is not a function' (7x, incluindo o import falho de buildDjenCertificationSql/resolveDjenEqualityMode) e 3 buscarProcesso que esperavam WHERE numero_processo = ?/regexp_replace explícitos mas recebiam sempre o SQL antigo incondicional. 95 testes pré-existentes continuaram passando (nenhuma regressão introduzida pelos novos testes em si)."
---

# RED: testes de igualdade direta antes da implementação

`Test Files 1 failed (1)` / `Tests 10 failed | 95 passed (105)`. As 10 falhas cobrem exatamente o comportamento novo pedido pelo goal: função pura ausente, builder de certificação ausente, e a ausência de ramificação direct/compatible em `buscarProcesso`.
