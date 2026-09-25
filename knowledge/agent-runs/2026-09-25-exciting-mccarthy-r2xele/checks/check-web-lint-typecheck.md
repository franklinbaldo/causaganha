---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-r2xele-check-web-lint-typecheck"
run_id: "2026-09-25-exciting-mccarthy-r2xele"
command: "cd web && npx eslint src/lib/processoCnj.ts src/lib/processoCnj.test.ts && npm run typecheck"
result: "passed"
summary: "eslint sobre os dois arquivos tocados nao reporta nenhum problema. astro check (typecheck) sobre o repositorio inteiro (152 arquivos) reporta 0 erros e 0 warnings -- os 5 hints reportados sao pre-existentes (Svelte $state/$derived em outros componentes, is:inline em advogados.astro/comparador.astro) e nao relacionados a esta mudanca."
---

# Check: eslint + astro check (web)

```
$ npx eslint src/lib/processoCnj.ts src/lib/processoCnj.test.ts
(sem output)

$ npm run typecheck
Result (152 files):
- 0 errors
- 0 warnings
- 5 hints
```
