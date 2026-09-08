---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-izm703-evidence-diff-fix"
run_id: "2026-09-08-exciting-mccarthy-izm703"
goal_id: "2026-09-08-exciting-mccarthy-izm703-goal-fix-absent-uploaded-double-count"
kind: "diff"
reference: "git diff -- web/src/queries/totals.qmd web/src/queries/tribunal_coverage.qmd web/src/queries/court_reliability.qmd"
summary: "Three one-line SQL changes, each adding 'AND ia_status != 'uploaded'' to an existing COUNT(*) FILTER (WHERE djen_status = 'absent' ...) clause, matching the guard already present on the 'pending' and 'unknown' filters two lines above in the same files. No Python, no frontend TypeScript/Svelte, no schema/contract changes -- net diff is 4 files changed (3 .qmd + the new test file), 116 insertions(+), 3 deletions(-)."
---

# Evidência: diff da correção

```diff
--- a/web/src/queries/totals.qmd
+++ b/web/src/queries/totals.qmd
@@
-  COUNT(*) FILTER (WHERE djen_status = 'absent') AS absent,
+  COUNT(*) FILTER (WHERE djen_status = 'absent' AND ia_status != 'uploaded') AS absent,

--- a/web/src/queries/tribunal_coverage.qmd
+++ b/web/src/queries/tribunal_coverage.qmd
@@
-  COUNT(*) FILTER (WHERE djen_status = 'absent') AS absent,
+  COUNT(*) FILTER (WHERE djen_status = 'absent' AND ia_status != 'uploaded') AS absent,

--- a/web/src/queries/court_reliability.qmd
+++ b/web/src/queries/court_reliability.qmd
@@
-    COUNT(*) FILTER (WHERE djen_status = 'absent') AS absent
+    COUNT(*) FILTER (WHERE djen_status = 'absent' AND ia_status != 'uploaded') AS absent
```

Correção mínima e cirúrgica: uma cláusula `AND` por arquivo, replicando a guarda já existente nos filtros `pending`/`unknown` vizinhos.
