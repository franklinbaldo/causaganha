---
type: AgentEvidence
id: "2026-09-10-exciting-mccarthy-25og4b-evidence-red-test"
run_id: "2026-09-10-exciting-mccarthy-25og4b"
goal_id: "2026-09-10-exciting-mccarthy-25og4b-goal-stj-timestamp-fixture"
kind: "test_red"
reference: "uv run pytest -q tests/causaganha/processos/test_query_plan_fixtures.py, run against the original DATE-typed query_plan_fixtures.py (before this round's fixture edit)"
summary: "Both new tests failed against the unmodified (DATE-typed) fixture. test_stj_date_columns_are_timestamp_typed failed with the columns reported as [('DATE',), ('DATE',)] instead of TIMESTAMP. test_stj_date_cast_is_distinguishable_from_varchar_cast failed with AssertionError: '2024-05-01' != '2024-05-01' -- proving directly that DATE-typed dataDecisao makes the ::DATE and ::VARCHAR casts produce the identical string, i.e. the exact gap this round's goal describes."
---

# Evidência RED

Comando: `uv run pytest -q tests/causaganha/processos/test_query_plan_fixtures.py` contra o `query_plan_fixtures.py` original (colunas `DATE`).

```
E       AssertionError: ::DATE and ::VARCHAR casts of STJ dataDecisao produced the same string (datetime.date(2024, 5, 1)); the fixture must carry a non-midnight TIMESTAMP so a ::DATE -> ::VARCHAR regression is actually detectable
E       assert '2024-05-01' != '2024-05-01'
```

Confirma exatamente o gap do goal: com a coluna `DATE`-tipada, um cast `::VARCHAR` defeituoso produziria a mesma string que o cast `::DATE` correto -- nenhum teste hoje pegaria essa regressão.
