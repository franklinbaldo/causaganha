---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-1a1ih8-evidence-red-publicacoes-order"
run_id: "2026-09-05-exciting-mccarthy-1a1ih8"
goal_id: "2026-09-05-exciting-mccarthy-1a1ih8-goal-publicacoes-search-first-hierarchy"
kind: "test_red"
reference: "cd web && npx vitest run src/pages/publicacoes/index.order.test.ts, run against the original (unmodified) web/src/pages/publicacoes/index.astro"
summary: "With the new test file written but web/src/pages/publicacoes/index.astro still in its original form (hero/lede+metrics, then the full 'Cobertura e lacunas por tribunal' attention-card, then <PublicationSearch client:load />), 2 of 3 assertions failed for the expected, concrete reason: 'renders the search action before the coverage/gaps explanation' failed with 'expected 2713 to be less than 2049' (the search marker's index in the source was numerically AFTER the coverage marker's), and 'keeps the search action immediately after the page header, with no attention-card in between' failed with 'expected false to be true' (an attention-card sat between the header and the search). The third assertion (the absence/backfill/failure distinction text is present) passed even before the reorder, since that text already existed in the file — only its position was wrong, confirming the test targets order specifically, not content presence."
---

# RED: ordem de `/publicacoes` falha antes da reordenação

`npx vitest run src/pages/publicacoes/index.order.test.ts` contra o arquivo original: 2 de 3 testes falham, exatamente pela ordem invertida (busca depois do card de cobertura, card de cobertura entre o cabeçalho e a busca). O terceiro teste (texto de distinção presente) já passava, confirmando que o RED é sobre ordem, não sobre conteúdo ausente.
