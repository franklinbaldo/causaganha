---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-qhtc8c-evidence-red-test"
run_id: "2026-09-09-exciting-mccarthy-qhtc8c"
goal_id: "2026-09-09-exciting-mccarthy-qhtc8c-goal-stj-date-cast-web-sql-twin"
kind: "test_red"
reference: "web/src/lib/processoCnj.test.ts -- 'stj query casts dataDecisao/dataPublicacao to DATE, not VARCHAR' and 'documentos query casts stj dataDecisao to DATE, not VARCHAR', run via `npx vitest run src/lib/processoCnj.test.ts -t \"casts\"` against unmodified processoCnj.ts"
summary: "Both new tests failed against the unmodified code, exactly as expected: assertion `expect(sql).toContain('MAX(\"dataDecisao\")::DATE AS data_decisao')` failed because the generated SQL contained `MAX(\"dataDecisao\")::VARCHAR AS data_decisao` instead, and the documentos-query assertion failed the same way for `\"dataDecisao\"::VARCHAR AS data`. 2 failed, 84 skipped."
---

# Evidencia RED

Os dois novos testes de asserção de texto SQL falharam contra o código não modificado, confirmando o cast `::VARCHAR` (em vez de `::DATE`) nos dois pontos de `buildStjSql`/`buildDocumentosSql`.
