---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-ich5gz-check-okf-structural"
run_id: "2026-09-05-exciting-mccarthy-ich5gz"
goal_id: "2026-09-05-exciting-mccarthy-ich5gz-goal-fonte-indisponivel-vs-ausente-parity"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: "2026-09-05-exciting-mccarthy-ich5gz-evidence-green-availability-parity"
summary: "conformant: true, 0 diagnostics, 149 concepts / 151 markdown docs / 2 reserved, run at session start after creating the four readings and the goal. Re-run at session end after populating decisions/evidence/checks and filling in run.md's remaining fields to confirm the fully-populated tree stays structurally conformant."
---

# Check: conformidade estrutural OKF

`okf-parser check` limpo no início da sessão (após leituras + goal) e reconfirmado no fechamento.
