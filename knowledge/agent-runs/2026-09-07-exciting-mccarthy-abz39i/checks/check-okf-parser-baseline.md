---
type: AgentCheck
id: "2026-09-07-exciting-mccarthy-abz39i-check-okf-parser-baseline"
run_id: "2026-09-07-exciting-mccarthy-abz39i"
goal_id: "2026-09-07-exciting-mccarthy-abz39i-goal-fix-pr-1247-http-health"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql (run after the four AgentReading files existed but before run.md)"
result: "observed"
evidence_id: "2026-09-07-exciting-mccarthy-abz39i-evidence-red-http-health"
summary: "4 OKF022 foreign-key diagnostics, all 'AgentReading_run_id_id_fkey' pointing at the not-yet-created AgentRun row for this round — expected while run.md is still being drafted, per the scaffold's own instructions. No other diagnostics. Used to confirm the schema check catches a real, expected gap before continuing."
---

# Check: baseline do okf-parser

4 diagnósticos OKF022 esperados (FK das `AgentReading` desta rodada apontando para um `AgentRun` que ainda não existe, porque `run.md` ainda não tinha sido escrito). Nenhum outro diagnóstico.
