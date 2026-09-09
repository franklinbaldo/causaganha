---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-qhtc8c-check-red-test"
run_id: "2026-09-09-exciting-mccarthy-qhtc8c"
goal_id: "2026-09-09-exciting-mccarthy-qhtc8c-goal-stj-date-cast-web-sql-twin"
command: "cd web && npm ci && npx vitest run src/lib/processoCnj.test.ts -t \"casts\""
result: "failed"
evidence_id: "2026-09-09-exciting-mccarthy-qhtc8c-evidence-red-test"
summary: "web/node_modules was not present in this fresh checkout; ran `npm ci` first (789 packages). 2 failed, 84 skipped -- both new SQL-cast assertions failed against unmodified processoCnj.ts, exactly as expected before the fix (found ::VARCHAR where ::DATE was asserted)."
---

# Check: teste RED

Confirma que os dois novos testes de asserção textual do SQL gerado falham contra a implementação original de `buildStjSql`/`buildDocumentosSql`.
