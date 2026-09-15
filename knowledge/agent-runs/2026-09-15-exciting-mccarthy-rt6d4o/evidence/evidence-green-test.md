---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-rt6d4o-evidence-green-test"
run_id: "2026-09-15-exciting-mccarthy-rt6d4o"
goal_id: "2026-09-15-exciting-mccarthy-rt6d4o-goal-direct-equality-processo-cnj"
kind: "test_green"
reference: "web/src/lib/processoCnj.ts (buildDjenSql, buildDjenCertificationSql, resolveDjenEqualityMode, resolveDjenEqualityModeLive, buscarProcesso)"
summary: "Após implementar os 4 símbolos novos e ligar resolveDjenEqualityModeLive em buscarProcesso: npx vitest run src/lib/processoCnj.test.ts -> 105/105 passando. Suite web completa (npx vitest run, 74 arquivos) -> 542/542. npm run lint (web/) -> 0 erros (43 warnings pré-existentes em styled-system/ gerado, não tocado). npm run typecheck (astro check) -> 0 erros, 0 warnings novos (só hints pré-existentes em arquivos não tocados)."
---

# GREEN: implementação completa, suíte web inteira verde

`Test Files 1 passed (1)` / `Tests 105 passed (105)` no arquivo tocado; `Test Files 74 passed (74)` / `Tests 542 passed (542)` na suíte web inteira. Nenhuma regressão nos testes pré-existentes de `buscarProcesso` (isolamento de falha por fonte, avisos, nucleoCompartilhado) -- a nova lógica de certificação é aditiva e cai no caminho compatível por padrão quando não há rota de mock para `parquet_kv_metadata`.
