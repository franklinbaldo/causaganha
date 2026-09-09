---
type: AgentDecision
id: "2026-09-09-exciting-mccarthy-qhtc8c-decision-cast-not-toisodate-rewrite"
run_id: "2026-09-09-exciting-mccarthy-qhtc8c"
goal_id: "2026-09-09-exciting-mccarthy-qhtc8c-goal-stj-date-cast-web-sql-twin"
question: "Fix the STJ date timezone-hazard by casting to ::DATE in the SQL (buildStjSql/buildDocumentosSql), or by rewriting toIsoDate() to stop reinterpreting a space-separated datetime string via `new Date(...)`?"
choice: "Cast to ::DATE in the SQL, at the exact two call sites that select the STJ date fields. Left toIsoDate() and every other caller of it untouched."
rationale: "A SQL-level ::DATE cast is the minimal, direct fix for the actual defect: it makes the STJ fields' shape match exactly what service.py's _stj_sql/_documentos_sql already produce (a bare calendar date, never a datetime-with-time), closing the gap between the two 'must stay in sync' implementations at its root rather than downstream. Rewriting toIsoDate() would be a strictly larger, riskier change: that function is shared by mapDjenRow, mapJurisRow, mapDatajudRow's data_ajuizamento, and mapDocumentoRow -- several of those fields are genuine timestamps or dates from other sources with their own casting conventions, and changing toIsoDate()'s parsing behavior to special-case space-separated strings would touch all of them at once without a single one of those call sites having the STJ-specific defect. The file already has a purpose-built function for the 'preserve time, don't reinterpret via Date()' case (toIsoTimestamp, used for datajud's ultima_atualizacao) -- but StjAcordaoView.dataDecisao/dataPublicacao are documented as calendar dates, not timestamps, so switching mapStjRow to toIsoTimestamp would change the view's output shape (adding a time component whenever the underlying column happens to be a TIMESTAMP) rather than just fixing the timezone bug. Casting to DATE in SQL is the only option that fixes the defect without changing any downstream type or shape contract."
---

# Decisao: consertar no SQL (cast) ou na funcao de mapeamento (toIsoDate)?

Escolhido fazer o cast `::DATE` diretamente nas duas queries (`buildStjSql`, `buildDocumentosSql`) em vez de reescrever `toIsoDate()`. E o ponto mais direto -- iguala exatamente o que `service.py` ja faz -- e evita alterar o comportamento de `toIsoDate()` para outros chamadores (`mapDjenRow`, `mapJurisRow`, `mapDatajudRow`, `mapDocumentoRow`) que nao tem esse defeito.
