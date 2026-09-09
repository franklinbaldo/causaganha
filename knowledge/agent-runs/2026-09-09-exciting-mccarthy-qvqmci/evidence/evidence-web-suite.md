---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-qvqmci-evidence-web-suite"
run_id: "2026-09-09-exciting-mccarthy-qvqmci"
goal_id: "2026-09-09-exciting-mccarthy-qvqmci-goal-stats-coverage-exclude-in-flight"
kind: "ci"
reference: "web/ -> npm test (vitest run)"
summary: "npm ci then npm test -> Test Files 70 passed (70), Tests 506 passed (506), Duration 34.07s. Includes the full contract-render integration suite (render_queries.py --strict against fixtures, all 19 .qmd contracts including stats_coverage.qmd re-rendered and schema-validated) with zero failures -- the modified stats_coverage.qmd still satisfies statsCoverageSchema in web/src/lib/data/contracts.ts (best_day/worst_day/best_count/worst_count remain nullable, unaffected by the FILTER addition returning NULL on an all-unsettled window)."
---

# Evidência: suíte web (vitest)

506 testes passam, incluindo o suite de integração que re-renderiza todos os `.qmd` contra fixtures e valida contra os schemas Zod -- `stats_coverage.qmd` modificado continua satisfazendo `statsCoverageSchema`.
