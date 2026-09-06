---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-iyujok-evidence-green-a11y-contract"
run_id: "2026-09-06-exciting-mccarthy-iyujok"
goal_id: "2026-09-06-exciting-mccarthy-iyujok-goal-mcpconfigcard-a11y"
kind: "test_green"
reference: "web/src/components/svelteA11y.contract.test.ts and web/src/components/McpConfigCard.test.ts, after web/src/components/McpConfigCard.svelte was fixed"
summary: "npx vitest run src/components/svelteA11y.contract.test.ts src/components/McpConfigCard.test.ts: 2 files passed, 7/7 tests passed — the new a11y contract test (0 warnings across all 35 .svelte files) and all 6 of McpConfigCard's pre-existing behavioral tests (display, exact-copy, success feedback, failure feedback, no-clipboard feedback, keyboard reachability), confirming the fix did not regress the component's existing copy-to-clipboard behavior. Full suites re-run afterward: npm run test — 59 files, 452/452 passed (up from 451, the +1 new test file), with the a11y compiler warning no longer present in stderr; npm run lint — 0 errors/43 pre-existing generated-file warnings (unchanged baseline); npm run typecheck — 0 errors/5 pre-existing hints (unchanged baseline)."
---

# Evidência GREEN: warning eliminado, comportamento preservado

Após a correção (`role="region"` + `aria-label` + `svelte-ignore` em `McpConfigCard.svelte`), o novo teste de contrato passa com 0 warnings de acessibilidade em todos os 35 componentes Svelte, e a suíte comportamental existente do próprio componente (6 casos) continua verde. A suíte completa do web subiu de 451 para 452 testes, todos passando, sem o warning do compilador no stderr.
