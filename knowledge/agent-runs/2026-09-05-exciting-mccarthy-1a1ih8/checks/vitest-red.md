---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-1a1ih8-check-vitest-red"
run_id: "2026-09-05-exciting-mccarthy-1a1ih8"
goal_id: "2026-09-05-exciting-mccarthy-1a1ih8-goal-publicacoes-search-first-hierarchy"
command: "cd web && npx vitest run src/pages/publicacoes/index.order.test.ts (against the original, unmodified index.astro)"
result: "failed"
evidence_id: "2026-09-05-exciting-mccarthy-1a1ih8-evidence-red-publicacoes-order"
summary: "2 of 3 tests failed for the expected reason (search rendered after, not before/immediately-after, the coverage attention-card). Confirms the new test is a real RED against real markup, not a tautology."
---

# Check: RED antes da reordenação

`npx vitest run src/pages/publicacoes/index.order.test.ts` falha 2/3 contra o arquivo original, pela ordem invertida esperada.
