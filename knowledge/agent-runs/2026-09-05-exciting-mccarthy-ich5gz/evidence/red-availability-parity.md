---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-ich5gz-evidence-red-availability-parity"
run_id: "2026-09-05-exciting-mccarthy-ich5gz"
goal_id: "2026-09-05-exciting-mccarthy-ich5gz-goal-fonte-indisponivel-vs-ausente-parity"
kind: "test_red"
reference: "git stash push -- scripts/processo_query_plan_compare.py scripts/processo_query_plan_fixture.py src/causaganha/processos/query_plan_fixtures.py web/src/lib/processoCnj.ts ; npx vitest run processoQueryPlanParity (web/)"
summary: "With the new test case present in processoQueryPlanParity.test.ts but the fixture/bridge/export implementation changes stashed away, the suite failed exactly as expected: 3 passed (the pre-existing cases, untouched), 1 failed — the new 'fonte registrada mas parquet indisponível' case, crashing inside scripts/processo_query_plan_compare.py with `_duckdb.IOException: IO Error: No files found that match the pattern \"None\"` (manifest.missing_djen_url was undefined, since the manifest-writer and fixture-builder changes were not yet applied). This is a genuine RED against the pre-implementation code, not a placeholder."
---

# RED: nova prova de disponibilidade falha antes da implementação

`vitest run processoQueryPlanParity` com o teste novo já escrito mas a implementação (fixture, bridge, export) revertida via `git stash`: 1 falha (a nova prova), 3 passam (as pré-existentes). Confirma que a prova exercita código real ainda não implementado, não uma tautologia.
