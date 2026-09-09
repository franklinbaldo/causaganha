---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-nnysz7-evidence-diff"
run_id: "2026-09-09-exciting-mccarthy-nnysz7"
goal_id: "2026-09-09-exciting-mccarthy-nnysz7-goal-totals-coverage-pct-null-not-nan"
kind: "diff"
reference: "web/src/queries/totals.qmd, tests/test_render_queries.py"
summary: "Two-file diff: totals.qmd's coverage_pct expression gains NULLIF(COUNT(*), 0) around the divisor, exactly mirroring site_status.qmd's own already-correct pattern; tests/test_render_queries.py gains one new fixture (manifest_parquet_empty, a genuine zero-row parquet with the canonical 6-column schema) and one new test. No other file touched -- an unrelated codegen drift in web/src/lib/djen-zod.gen.ts (from a locally mismatched orval version, reverted via git checkout --) was excluded to keep the PR scoped to the verified bug."
---

# Evidência: diff

```diff
--- a/web/src/queries/totals.qmd
+++ b/web/src/queries/totals.qmd
@@ -15,7 +15,7 @@ SELECT
   COUNT(*) FILTER (WHERE djen_status IN ('available', 'confirmed') AND ia_status != 'uploaded') AS pending,
   COUNT(*) FILTER (WHERE djen_status = 'absent' AND ia_status != 'uploaded') AS absent,
   COUNT(*) FILTER (WHERE COALESCE(djen_status, '') = '' AND ia_status != 'uploaded') AS unknown,
-  ROUND(100.0 * COUNT(*) FILTER (WHERE ia_status = 'uploaded') / COUNT(*), 1) AS coverage_pct,
+  ROUND(100.0 * COUNT(*) FILTER (WHERE ia_status = 'uploaded') / NULLIF(COUNT(*), 0), 1) AS coverage_pct,
   COUNT(DISTINCT tribunal) AS tribunals_total,
   COUNT(DISTINCT tribunal) FILTER (WHERE ia_status = 'uploaded') AS tribunals_with_data
 FROM manifest;
```

(tests/test_render_queries.py diff: +56 lines -- one fixture, one test; see evidence-red-test.md / evidence-green-test.md for behavior.)
