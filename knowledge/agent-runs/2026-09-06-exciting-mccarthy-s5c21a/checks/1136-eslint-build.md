---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-s5c21a-check-1136-eslint-build"
run_id: "2026-09-06-exciting-mccarthy-s5c21a"
goal_id: "2026-09-06-exciting-mccarthy-s5c21a-goal-1136-minhas-consultas-query-states"
command: "cd web && npx eslint . ; npm run build (after uv run python scripts/render_queries.py)"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-s5c21a-evidence-1136-full-gates-green"
summary: "eslint: 0 errors, 43 pre-existing warnings confined to generated styled-system/*.d.ts. build: 120 pages built, Complete!"
---

# Check: eslint e build estático
