---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-p973xb-check-web-lint-typecheck"
run_id: "2026-09-24-exciting-mccarthy-p973xb"
command: "cd web && npm run lint && npm run typecheck"
result: "passed"
summary: "eslint: 0 errors (43 warnings pre-existentes, todos em arquivos gerados/vendorizados sob styled-system/ e 2 testes de referencia nao tocados por esta mudanca -- nenhum novo warning introduzido por PublicationSearch.svelte/PublicationSearch.export.test.ts). astro check: 0 errors, 0 warnings, 5 hints pre-existentes (nenhum em arquivos tocados por esta mudanca)."
---

# Check: lint e typecheck do web apos a correcao de #1612

```
$ npm run lint
✖ 43 problems (0 errors, 43 warnings)

$ npm run typecheck
Result (152 files):
- 0 errors
- 0 warnings
- 5 hints
```
