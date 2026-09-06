---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-iyujok-evidence-red-a11y-contract"
run_id: "2026-09-06-exciting-mccarthy-iyujok"
goal_id: "2026-09-06-exciting-mccarthy-iyujok-goal-mcpconfigcard-a11y"
kind: "test_red"
reference: "web/src/components/svelteA11y.contract.test.ts (written before web/src/components/McpConfigCard.svelte was fixed)"
summary: "npx vitest run src/components/svelteA11y.contract.test.ts failed with exactly one a11y warning collected across all 35 .svelte files under web/src: 'components/McpConfigCard.svelte: [a11y_no_noninteractive_tabindex] noninteractive element cannot have nonnegative tabIndex value'. This matches byte-for-byte the warning npm run test's own stderr had already surfaced ('src/components/McpConfigCard.svelte:47:2 noninteractive element cannot have nonnegative tabIndex value'), confirming the new contract test targets the real, pre-existing defect and not a synthetic one. First attempt at the test (checking every compiler warning code, not just a11y_*) also failed but for unrelated, pre-existing state_referenced_locally warnings in DateDetail.svelte/TribunalCoverageExplorer.svelte/TribunalDetail.svelte/YearSummaryCards.svelte — narrowed the test to a11y_* codes specifically to keep this round's contract scoped to the actual accessibility defect being fixed, not scope-creep into unrelated stylistic warnings in components untouched by this goal."
---

# Evidência RED: warning de acessibilidade real capturado pelo novo teste de contrato

O teste `svelteA11y.contract.test.ts`, rodado antes da correção, falhou reportando exatamente o warning `a11y_no_noninteractive_tabindex` em `McpConfigCard.svelte` — o mesmo já visível no stderr do `npm run test` de linha de base. A primeira versão do teste (sem filtro por `a11y_*`) também capturava warnings `state_referenced_locally` pré-existentes e não relacionados em outros componentes; restringi o teste ao prefixo `a11y_` para manter o escopo desta rodada no defeito real de acessibilidade, sem se meter em ruído estilístico de componentes fora do objetivo.
