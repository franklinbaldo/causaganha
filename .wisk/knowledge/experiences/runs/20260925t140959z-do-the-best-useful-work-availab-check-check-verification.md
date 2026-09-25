---
type: "RunCheck"
id: "run-checks/20260925t140959z-do-the-best-useful-work-availab/check-verification"
run: "runs/20260925T140959Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check; uv run ruff format --check; uv run pytest -q (suite completa); cd web && npx vitest run src/lib/processoCnj.test.ts; npm run typecheck"
result: "Todos verdes: ruff check 'All checks passed!'; ruff format --check limpo (462 arquivos formatados, 1 reformatado durante a implementacao e ja corrigido); pytest -q completo exit 0, 100% dos testes coletados passando; vitest processoCnj.test.ts 155/155 passando; astro check (typecheck) 0 erros/0 warnings novos."
status: "pass"
evidence: "run-evidence/20260925t140959z-do-the-best-useful-work-availab/evidence-green-tm04-juris"
goal: "run-goals/20260925t140959z-do-the-best-useful-work-availab/goal-tm04-juris-read-side"
---

# RunCheck
