---
type: "RunCheck"
id: "run-checks/20260907t112418z-fa-a-o-melhor-avan-o-poss-vel-n/check-web-suite-green"
run: "runs/20260907T112418Z-fa-a-o-melhor-avan-o-poss-vel-neste-reposit-rio"
kind: "verification"
procedure: "cd web && npm test && npx astro check && npm run lint (mesmos comandos usados pelo job CI 'web'); tambem 'uv run ruff check && uv run ruff format --check && uv run pytest -q' na raiz para garantir que a mudanca web nao afeta o lado Python"
result: "489/489 testes vitest passam (487 antes + 2 novos), 'npx astro check' 0 erros/0 avisos, eslint 0 erros (so os 43 avisos preexistentes em .d.ts gerados por Panda). Na raiz: ruff check e ruff format --check passam, pytest -q 100% (todas as suites, sem regressao)."
status: "pass"
evidence: "evidence-green-alertbanner-test"
goal: "goal-fix-alertbanner-reactivity"
---

# RunCheck
