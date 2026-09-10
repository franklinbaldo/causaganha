---
type: AgentEvidence
id: "2026-09-10-exciting-mccarthy-8042ey-evidence-diff"
run_id: "2026-09-10-exciting-mccarthy-8042ey"
goal_id: "2026-09-10-exciting-mccarthy-8042ey-goal-writeback-constants-drift"
kind: "diff"
reference: "scripts/render_manifest_parquet.py (write_back_csv), tests/test_render_manifest_writeback.py"
summary: "git diff scripts/render_manifest_parquet.py: write_back_csv's djen_raw ibis.cases() predicate/output changed from the hardcoded literals (manifest.djen_status == \"absent\") & ((manifest.djen_raw == \"200\") | manifest.djen_raw.startswith(\"200:\")) -> \"no_publications\" to the imported constants (manifest.djen_status == ABSENT) & ((manifest.djen_raw == BARE_200_RAW) | manifest.djen_raw.startswith(PREFIXED_200_RAW_PREFIX)) -> NO_PUBLICATIONS_SENTINEL. 9 lines changed (+6/-3), no behavior change for the real constant values, only removes the re-typed duplication of the contract already enforced correctly by _normalize_manifest a few lines above in the same file. tests/test_render_manifest_writeback.py: +50 lines, one new test (test_write_back_derives_from_absent_consistency_constants_not_retyped_literals) monkeypatching the four constants and asserting derivation."
---

# Evidência de diff

```diff
diff --git a/scripts/render_manifest_parquet.py b/scripts/render_manifest_parquet.py
index bec4d45..9af3a85 100644
--- a/scripts/render_manifest_parquet.py
+++ b/scripts/render_manifest_parquet.py
@@ -518,9 +518,12 @@ def write_back_csv(con: duckdb.DuckDBPyConnection) -> Path:
         ),
         djen_raw=ibis.cases(
             (
-                (manifest.djen_status == "absent")
-                & ((manifest.djen_raw == "200") | manifest.djen_raw.startswith("200:")),
-                "no_publications",
+                (manifest.djen_status == ABSENT)
+                & (
+                    (manifest.djen_raw == BARE_200_RAW)
+                    | manifest.djen_raw.startswith(PREFIXED_200_RAW_PREFIX)
+                ),
+                NO_PUBLICATIONS_SENTINEL,
             ),
             else_=manifest.djen_raw,
         ),
```

Arquivo de teste: `tests/test_render_manifest_writeback.py` ganhou `test_write_back_derives_from_absent_consistency_constants_not_retyped_literals` (50 linhas), que monkeypatcha `ABSENT`/`BARE_200_RAW`/`PREFIXED_200_RAW_PREFIX`/`NO_PUBLICATIONS_SENTINEL` no módulo carregado e confirma que `write_back_csv` segue os valores corrigidos.
