---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-sk8ec6-evidence-red-tests"
run_id: "2026-09-06-exciting-mccarthy-sk8ec6"
goal_id: "2026-09-06-exciting-mccarthy-sk8ec6-goal-fix-1193-dataset-availability"
kind: "test_red"
reference: "web/src/components/DuckDBExplorer.dataset-availability.test.ts, run against pre-fix DuckDBExplorer.svelte via `npx vitest run src/components/DuckDBExplorer.dataset-availability.test.ts`"
summary: "Wrote 6 tests encoding #1193's acceptance criteria before touching the component. Against the unmodified component: the 2 tests for already-correct behavior (404 and no-parquet-metadata both classify as 'missing') passed immediately; the 4 tests for the missing behavior (5xx classifies as 'unavailable' not 'missing'; network failure classifies as 'unavailable'; a transient failure is not cached and a retry button can recover to 'ready'; tribunal/year selection survives an 'unavailable' classification) failed with `waitFor` timeouts because no 'unavailable' state, no distinct message, and no 'Tentar verificar novamente' button existed in the component — confirming a true RED for exactly the behavior #1193 asks for, with no false failures once a test-harness bug (selecting an option before the async tribunal/year fetch had populated it) was fixed by waiting for options to exist before firing the change event."
---

# Evidência: testes RED

6 testes escritos a partir dos critérios de aceite da `#1193`. Contra o componente original: 2 passam (já corretos), 4 falham por timeout (`unavailable`, mensagem distinta, botão de retry inexistentes) — RED real, sem falsos positivos após corrigir um bug do próprio harness de teste (selecionar opção antes do fetch assíncrono popular o `<select>`).
