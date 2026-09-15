---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-rt6d4o-check-web-suite-green"
run_id: "2026-09-15-exciting-mccarthy-rt6d4o"
goal_id: "2026-09-15-exciting-mccarthy-rt6d4o-goal-direct-equality-processo-cnj"
command: "cd web && npx vitest run && npm run lint && npm run typecheck"
result: "passed"
evidence_id: "2026-09-15-exciting-mccarthy-rt6d4o-evidence-green-test"
summary: "npx vitest run: 74 arquivos / 542 testes, todos verdes. npm run lint (eslint): 0 erros (43 warnings pré-existentes em styled-system/*.d.ts gerado, não tocado nesta rodada). npm run typecheck (astro check): 0 erros, 0 warnings novos (5 hints pré-existentes em arquivos não tocados: PublicationActions.reference.test.ts, PublicationCard.reference.test.ts, advogados.astro, comparador.astro)."
---

# Check: suíte web completa + lint + typecheck

Confirma que a implementação de igualdade direta em `processoCnj.ts` não introduziu regressão em nenhum dos 542 testes web nem em lint/typecheck.
