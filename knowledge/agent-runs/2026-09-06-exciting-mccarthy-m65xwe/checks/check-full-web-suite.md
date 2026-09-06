---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-m65xwe-check-full-web-suite"
run_id: "2026-09-06-exciting-mccarthy-m65xwe"
goal_id: "2026-09-06-exciting-mccarthy-m65xwe-goal-typecheck-debt-and-ci-gate"
command: "cd web && npm test && npm run lint && npm run build"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-m65xwe-evidence-full-suite-green"
summary: "vitest 435/435 passed, eslint 0 errors (43 pre-existing unrelated warnings), astro build completed 109 pages with the same CI-style public/data/ stub JSON files .github/workflows/test.yml generates."
---

# Check: suíte completa do web/ sem regressão
