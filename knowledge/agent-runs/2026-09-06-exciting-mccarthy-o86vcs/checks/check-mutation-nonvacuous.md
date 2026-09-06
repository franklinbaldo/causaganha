---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-o86vcs-check-mutation-nonvacuous"
run_id: "2026-09-06-exciting-mccarthy-o86vcs"
goal_id: "2026-09-06-exciting-mccarthy-o86vcs-goal-quick-range-coverage"
command: "Two rounds of: edit useRecentDays() with a deliberate bug -> npm test -- --run src/components/TribunalCoverageExplorer.test.ts -> cp back from backup -> diff (byte-identical)"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-o86vcs-evidence-red-quick-range-mutation"
summary: "Mutation 1 (off-by-one day count): 4 tests failed, 11 passed. Mutation 2 (UTC arithmetic, local-getter formatting): 1 test failed (the TZ=America/Los_Angeles boundary case), 14 passed. Both mutations reverted and confirmed byte-identical to the pre-mutation file via diff before proceeding."
---

# Check: prova de não-vacuidade por mutação

Cada nova asserção falha sob pelo menos uma mutação plausível, e cada mutação derruba exatamente o subconjunto de testes esperado — nenhum teste é redundante ou vazio.
