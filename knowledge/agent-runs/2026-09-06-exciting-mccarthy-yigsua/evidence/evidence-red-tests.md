---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-yigsua-evidence-red-tests"
run_id: "2026-09-06-exciting-mccarthy-yigsua"
goal_id: "2026-09-06-exciting-mccarthy-yigsua-goal-fix-1197-query-error-classification"
kind: "test_red"
reference: "web/src/components/DuckDBExplorer.query-error-classification.test.ts (written before any production-code change); npx vitest run src/components/DuckDBExplorer.query-error-classification.test.ts"
summary: "6 new tests against the pre-fix runQuery() catch block: 4 failed exactly as the bug predicts ('does not classify a transient 5xx error...', 'does not classify a network failure...', 'preserves tribunal/year selection...', 'allows retrying execution...' — all timed out waiting for the 'instabilidade temporária' text because the old code showed 'não encontrado no Internet Archive' instead), while 2 passed by coincidence with the desired behavior (the unambiguous 404 case, and the local-SQL-error case, since neither happened to trip the old code's own false branches). Confirms the RED state matches the bug described in #1197 precisely, not a test-authoring artifact."
---

# Evidência — testes RED (#1197)

4 de 6 testes falharam no componente original, exatamente nos casos que a `#1197` descreve (erro 5xx/rede tratado como "dataset ausente"); os outros 2 já passavam por já corresponderem ao comportamento correto por acidente (404 inequívoco, erro SQL local).
