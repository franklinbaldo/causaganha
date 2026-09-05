---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-1a1ih8-check-vitest-green"
run_id: "2026-09-05-exciting-mccarthy-1a1ih8"
goal_id: "2026-09-05-exciting-mccarthy-1a1ih8-goal-publicacoes-search-first-hierarchy"
command: "cd web && npx vitest run src/pages/publicacoes/index.order.test.ts (after reordering index.astro)"
result: "passed"
evidence_id: "2026-09-05-exciting-mccarthy-1a1ih8-evidence-green-publicacoes-order"
summary: "3/3 passing after moving <PublicationSearch> immediately after the page-head and the coverage attention-card below it, while keeping the absence/backfill/failure distinction text intact."
---

# Check: GREEN após a reordenação

`npx vitest run src/pages/publicacoes/index.order.test.ts` passa 3/3 após o reorder.
