---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-akb9oz-check-web-lint-typecheck"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
command: "cd web && npx eslint . && npx astro check"
result: "passed"
summary: "eslint: 0 erros (43 warnings pre-existentes em arquivos gerados styled-system/*.d.ts, nao relacionados a esta mudanca -- 'Unused eslint-disable directive'). astro check: 0 erros, 0 warnings, 3 hints (todos pre-existentes em *.reference.test.ts, 'await has no effect', nao tocados por esta rodada)."
---

# Check: eslint + astro check (typecheck), final

```
$ npx eslint .
✖ 43 problems (0 errors, 43 warnings)

$ npx astro check
Result (157 files):
- 0 errors
- 0 warnings
- 3 hints
```
