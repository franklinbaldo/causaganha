---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-3kjpfr-check-full-suite-lint-typecheck-build"
run_id: "2026-09-06-exciting-mccarthy-3kjpfr"
goal_id: "2026-09-06-exciting-mccarthy-3kjpfr-goal-drilldown-cobertura-por-tribunal"
command: "cd web && npm run test && npm run lint && npm run typecheck && (cd .. && uv run python scripts/render_queries.py) && npm run build"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-3kjpfr-evidence-full-suite-and-build-with-real-data"
summary: "vitest: 405/405 passed across 50 files. eslint: 0 errors. astro check (svelte-check): 19 errors, identical to the pre-change baseline (verified by stashing this round's files and re-running). Static build: 120 pages, including /stats.html with the new drill-down section, built successfully against regenerated real production contract data."
---

# Check: suíte completa, lint, typecheck e build
