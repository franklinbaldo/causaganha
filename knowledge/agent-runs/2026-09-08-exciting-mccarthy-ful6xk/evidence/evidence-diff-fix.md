---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-ful6xk-evidence-diff-fix"
run_id: "2026-09-08-exciting-mccarthy-ful6xk"
goal_id: "2026-09-08-exciting-mccarthy-ful6xk-goal-fix-tribunal-completion-formula"
kind: "diff"
reference: "git diff web/src/lib/coverageInsights.ts"
summary: "One-line fix: `(params.coverageSize / params.expectedDays) * 100` becomes `((params.coverageSize + params.absentCount) / params.expectedDays) * 100` in buildTribunalAttentionCards()'s completion calculation (line 172). Plus a new test file web/src/lib/coverageInsights.test.ts (RED then GREEN, 2 tests) — the function had zero test coverage before this round."
---

# Evidência: diff da correção

```diff
   const completion = params.expectedDays > 0
-    ? (params.coverageSize / params.expectedDays) * 100
+    ? ((params.coverageSize + params.absentCount) / params.expectedDays) * 100
     : params.completionPct;
```
