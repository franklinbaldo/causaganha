---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-ucw90y-check-publicacoes-order-test-diff"
run_id: "2026-09-06-exciting-mccarthy-ucw90y"
goal_id: "2026-09-06-exciting-mccarthy-ucw90y-goal-review-pr-1169"
command: "git diff d2a4530..origin/reboot/cobogo-web -- web/src/pages/publicacoes/index.astro web/src/pages/publicacoes/_index.order.test.ts"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-ucw90y-evidence-publicacoes-order-preserved"
summary: "Confirms the new template renders <PublicationSearch client:load /> before the coverage alert block, and the dedicated order test was updated (not deleted) to assert the same ordering with new text markers."
---

# Check — ordem ação-antes-de-cobertura confirmada no diff
