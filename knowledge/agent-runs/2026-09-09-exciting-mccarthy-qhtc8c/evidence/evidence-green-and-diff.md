---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-qhtc8c-evidence-green-and-diff"
run_id: "2026-09-09-exciting-mccarthy-qhtc8c"
goal_id: "2026-09-09-exciting-mccarthy-qhtc8c-goal-stj-date-cast-web-sql-twin"
kind: "diff"
reference: "git diff web/src/lib/processoCnj.ts (2 hunks, 4 lines changed) plus web/src/lib/processoCnj.test.ts (+22 lines, 2 new tests)"
summary: "Fix: buildStjSql()'s `MAX(\"dataDecisao\")::VARCHAR AS data_decisao` / `MAX(\"dataPublicacao\")::VARCHAR AS data_publicacao` became `::DATE`; buildDocumentosSql()'s stj branch `\"dataDecisao\"::VARCHAR AS data` became `::DATE`. After the fix: `npx vitest run src/lib/processoCnj.test.ts` -- 86/86 passed (was 84 passed/2 failed before the fix). `npx vitest run src/lib/processoQueryPlanParity.test.ts` (run from web/, real DuckDB execution of both Python and JS SQL text against the same Python-built fixture parquets) -- 4/4 passed, confirming the DATE cast doesn't change any Python/JS row-equality outcome (the shared fixture hardcodes STJ dates as DATE literals, so both casts already produced identical strings there -- this is the exact test-fixture blind spot the investigating Explore-agent flagged, not resolved by this minimal fix). Full `npx vitest run` in web/ -- 71 files / 510 tests passed. No Python file touched by this change."
---

# Evidencia GREEN + diff

Apos o fix (`::VARCHAR` -> `::DATE` nos dois pontos), os dois novos testes RED passam, a suite completa de `processoCnj.test.ts` (86 testes) permanece verde, o harness de paridade cross-runtime (`processoQueryPlanParity.test.ts`, execução real via DuckDB contra fixtures Python) permanece verde (4/4), e a suite completa do frontend (510 testes) permanece verde.
