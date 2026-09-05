---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-ejibsp-evidence-ci-wiring"
run_id: "2026-09-05-exciting-mccarthy-ejibsp"
goal_id: "2026-09-05-exciting-mccarthy-ejibsp-goal-extend-completeness-checker"
kind: "diff"
reference: ".github/workflows/okf.yml"
summary: "Added a 'Check AgentRun-family round reports are complete' step (uv run --project .okf-parser --frozen python scripts/check_agent_run_completeness.py knowledge/agent-runs) right after the existing okf-parser relational check, following the same --project .okf-parser convention already used by the generated-model steps in this workflow. Also added scripts/check_agent_run_completeness.py to the workflow's own path triggers so a change to the checker itself re-runs the gate. This makes an incomplete Agent*-typed round report fail CI on any PR touching knowledge/**, closing PR #1144's recorded next_move ('wire it into CI')."
---

# Evidência: checador de completude ligado ao CI
