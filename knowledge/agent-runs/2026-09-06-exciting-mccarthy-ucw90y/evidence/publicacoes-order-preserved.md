---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-ucw90y-evidence-publicacoes-order-preserved"
run_id: "2026-09-06-exciting-mccarthy-ucw90y"
goal_id: "2026-09-06-exciting-mccarthy-ucw90y-goal-review-pr-1169"
kind: "diff"
reference: "web/src/pages/publicacoes/index.astro:20-42 and web/src/pages/publicacoes/_index.order.test.ts (reboot/cobogo-web head)"
summary: "The new /publicacoes template renders <PublicationSearch client:load /> inside a section that appears before the coverage alert block (text 'Cobertura não é uma promessa de completude.'). The dedicated order test (_index.order.test.ts, tied to issue #1139) was updated in this PR to match the new hero/search/coverage text markers and asserts searchIndex < coverageIndex and heroIndex < searchIndex < coverageAlertIndex. This satisfies point 3 of the owner's review request (action/result before coverage)."
---

# Evidência — ordem ação-antes-de-cobertura preservada em `/publicacoes`

O teste `_index.order.test.ts` foi atualizado para os novos marcadores de texto e continua verificando a ordem correta (busca antes de cobertura).
