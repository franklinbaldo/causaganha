---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-qhtc8c-check-green-test"
run_id: "2026-09-09-exciting-mccarthy-qhtc8c"
goal_id: "2026-09-09-exciting-mccarthy-qhtc8c-goal-stj-date-cast-web-sql-twin"
command: "cd web && npx vitest run src/lib/processoCnj.test.ts"
result: "passed"
evidence_id: "2026-09-09-exciting-mccarthy-qhtc8c-evidence-green-and-diff"
summary: "86/86 passed after changing buildStjSql()'s and buildDocumentosSql()'s ::VARCHAR casts on dataDecisao/dataPublicacao to ::DATE -- both new RED tests now pass, and none of the file's 84 pre-existing tests regressed."
---

# Check: teste GREEN

Confirma que os dois testes RED passam após o fix (`::VARCHAR` -> `::DATE`), sem regressão nos demais 84 testes do arquivo.
