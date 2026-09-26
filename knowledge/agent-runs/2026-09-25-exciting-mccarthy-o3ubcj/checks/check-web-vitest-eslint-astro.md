---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-o3ubcj-check-web-vitest-eslint-astro"
run_id: "2026-09-25-exciting-mccarthy-o3ubcj"
command: "cd web && npx vitest run && npx eslint src/lib/processoCnj.ts src/lib/processoCnj.test.ts && npx astro check"
result: "passed"
summary: "vitest: 80 arquivos, 624 testes, 100% verde. eslint sobre os dois arquivos tocados: 0 erros. astro check (repositório inteiro): 157 arquivos, 0 erros, 0 warnings, 3 hints pré-existentes (await sem efeito em arquivos .reference.test.ts não tocados por esta rodada)."
evidence_id: "2026-09-25-exciting-mccarthy-o3ubcj-evidence-green-test"
---

# Check: vitest + eslint + astro check (lado Web)
