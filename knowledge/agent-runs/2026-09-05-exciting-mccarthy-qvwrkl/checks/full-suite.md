---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-qvwrkl-check-full-suite"
run_id: "2026-09-05-exciting-mccarthy-qvwrkl"
goal_id: "2026-09-05-exciting-mccarthy-qvwrkl-goal-publicacoes-copy-reference"
command: "cd web && npx vitest run && npm run lint; cd .. && uv run ruff check && uv run ruff format --check"
result: "passed"
evidence_id: "2026-09-05-exciting-mccarthy-qvwrkl-evidence-full-suite"
summary: "340/340 vitest tests, eslint clean, ruff check and ruff format --check clean on the unchanged Python tree."
---

# Check: suíte completa e lint
