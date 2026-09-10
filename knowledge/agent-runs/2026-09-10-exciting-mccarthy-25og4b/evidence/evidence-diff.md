---
type: AgentEvidence
id: "2026-09-10-exciting-mccarthy-25og4b-evidence-diff"
run_id: "2026-09-10-exciting-mccarthy-25og4b"
goal_id: "2026-09-10-exciting-mccarthy-25og4b-goal-stj-timestamp-fixture"
kind: "diff"
reference: "git diff src/causaganha/processos/query_plan_fixtures.py + new file tests/causaganha/processos/test_query_plan_fixtures.py"
summary: "query_plan_fixtures.py's STJ VALUES rows now use TIMESTAMP '... HH:MM:SS' literals (non-midnight, distinct per row) for dataDecisao/dataPublicacao instead of DATE '...', with a comment explaining why. New test file tests/causaganha/processos/test_query_plan_fixtures.py (2 tests) asserts the columns are TIMESTAMP-typed and directly demonstrates the ::DATE vs ::VARCHAR cast divergence the fixture now supports."
---

# Evidência diff

```diff
diff --git a/src/causaganha/processos/query_plan_fixtures.py b/src/causaganha/processos/query_plan_fixtures.py
index 353402a..5c8b9b8 100644
--- a/src/causaganha/processos/query_plan_fixtures.py
+++ b/src/causaganha/processos/query_plan_fixtures.py
@@ -85,16 +85,22 @@ def build_fixtures(tmp_path: Path) -> dict[str, Path]:
                data_julgamento, texto_limpo, url_portal)
         """,
     )
+    # dataDecisao/dataPublicacao are TIMESTAMP (not DATE) with a non-midnight
+    # time-of-day on purpose: service.py's _stj_sql/_documentos_sql and
+    # processoCnj.ts's buildStjSql both cast these with ::DATE, and a DATE
+    # column would make that cast indistinguishable from a buggy ::VARCHAR
+    # one (both produce the same 'YYYY-MM-DD' string) — see
+    # tests/causaganha/processos/test_query_plan_fixtures.py.
     stj = copy_to_parquet(
         tmp_path / "stj-acordaos.parquet",
         f"""
         SELECT * FROM (VALUES
             ('stj-1', '{CNJ_ALL}', 'REsp', 'MIN X', 'tema', 'tese', 'ementa',
-             DATE '2024-05-01', DATE '2024-05-10'),
+             TIMESTAMP '2024-05-01 14:23:05', TIMESTAMP '2024-05-10 09:00:00'),
             ('stj-2', '{CNJ_TIEBREAK}', 'AgInt', 'MIN Y', 'tema antigo', 'tese antiga',
-             'ementa antiga', DATE '2023-01-01', DATE '2023-01-10'),
+             'ementa antiga', TIMESTAMP '2023-01-01 08:00:00', TIMESTAMP '2023-01-10 08:00:00'),
             ('stj-3', '{CNJ_TIEBREAK}', 'REsp', 'MIN Z', 'tema recente', 'tese recente',
-             'ementa recente', DATE '2024-06-01', DATE '2024-06-10')
+             'ementa recente', TIMESTAMP '2024-06-01 08:00:00', TIMESTAMP '2024-06-10 08:00:00')
         ) AS t(id, "numeroProcesso", "siglaClasse", "ministroRelator", tema,
                "teseJuridica", ementa, "dataDecisao", "dataPublicacao")
         """,
```

Novo arquivo `tests/causaganha/processos/test_query_plan_fixtures.py` (2 testes): `test_stj_date_columns_are_timestamp_typed` introspecciona o schema do parquet via `DESCRIBE`; `test_stj_date_cast_is_distinguishable_from_varchar_cast` roda os dois casts (`::DATE` e `::VARCHAR`) contra o fixture e afirma que divergem, replicando exatamente o cast usado por `service.py`/`processoCnj.ts`.
