---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-ich5gz-check-vitest-red"
run_id: "2026-09-05-exciting-mccarthy-ich5gz"
goal_id: "2026-09-05-exciting-mccarthy-ich5gz-goal-fonte-indisponivel-vs-ausente-parity"
command: "git stash push -- scripts/processo_query_plan_compare.py scripts/processo_query_plan_fixture.py src/causaganha/processos/query_plan_fixtures.py web/src/lib/processoCnj.ts && (cd web && npx vitest run processoQueryPlanParity)"
result: "failed"
evidence_id: "2026-09-05-exciting-mccarthy-ich5gz-evidence-red-availability-parity"
summary: "1 of 4 tests failed (the new availability-parity case) with the pre-implementation code stashed away; the 3 pre-existing cases in the same file kept passing. Confirms the new test is a real RED, not a tautology."
---

# Check: RED antes da implementação

Confirma que o novo teste falha por ausência de implementação real (campo de manifest indefinido → `read_parquet(['None'])`), não por erro de sintaxe do próprio teste.
