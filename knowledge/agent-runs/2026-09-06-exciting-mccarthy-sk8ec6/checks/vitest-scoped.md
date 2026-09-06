---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-sk8ec6-check-vitest-scoped"
run_id: "2026-09-06-exciting-mccarthy-sk8ec6"
goal_id: "2026-09-06-exciting-mccarthy-sk8ec6-goal-fix-1193-dataset-availability"
command: "npx vitest run src/components/DuckDBExplorer.dataset-availability.test.ts --reporter=verbose (web/)"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-sk8ec6-evidence-green-tests"
summary: "6/6 tests pass, run twice: once RED against the unmodified component (2 pass, 4 fail as expected), once GREEN after the fix (6/6 pass). Command and full output captured in evidence/red-tests.md and evidence/green-tests.md."
---

# Check: vitest (arquivo de teste da `#1193`)

RED (2/6) → GREEN (6/6), confirmado via execução direta do arquivo de teste isolado.
