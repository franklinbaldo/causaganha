---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-tp38w3-check-full-suite-typecheck-lint-build"
run_id: "2026-09-06-exciting-mccarthy-tp38w3"
goal_id: "2026-09-06-exciting-mccarthy-tp38w3-goal-mostrar-mudancas-desde-ultima-consulta"
command: "cd web && npx vitest run && npx svelte-check --tsconfig ./tsconfig.json && npx eslint . && uv run python ../scripts/render_queries.py && npm run build"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-tp38w3-evidence-full-suite-and-static-checks-green"
summary: "vitest: 48 files / 388 tests, all green. svelte-check: 37 errors (compared against a 38-error baseline measured on the same commit with this round's diff stashed) — no new error survives after fixing the {@const} placement/narrowing issue this round's template introduced. eslint: 0 errors. Static build: 120 pages, after regenerating web/public/data/*.json via scripts/render_queries.py."
---

# Check: suíte completa, typecheck, lint e build estático
