---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-m65xwe-check-okf-parser"
run_id: "2026-09-06-exciting-mccarthy-m65xwe"
goal_id: "2026-09-06-exciting-mccarthy-m65xwe-goal-typecheck-debt-and-ci-gate"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-m65xwe-evidence-okf-conformant"
summary: "conformant: true, 0 diagnostics, 424 concepts. Re-run repeatedly through this round's own scaffold-then-fill loop; the only diagnostics ever seen were the expected transient FK errors before run.md's frontmatter existed (see reading-okf.md), resolved once run.md was filled."
---

# Check: okf-parser conformante ao longo da rodada
