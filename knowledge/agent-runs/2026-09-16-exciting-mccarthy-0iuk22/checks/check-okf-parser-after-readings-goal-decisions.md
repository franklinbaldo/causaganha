---
type: AgentCheck
id: "2026-09-16-exciting-mccarthy-0iuk22-check-okf-parser-after-readings-goal-decisions"
run_id: "2026-09-16-exciting-mccarthy-0iuk22"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "failed"
summary: "First run after readings/goal/decisions/evidence were written but before run.md existed: 10 OKF022 foreign-key errors, one per AgentReading/AgentGoal/AgentDecision/AgentEvidence file, all 'no matching AgentRun(id) for (2026-09-16-exciting-mccarthy-0iuk22)' -- the scaffold's own first-action instruction (copy the scaffold to run.md) had not actually been done yet. Fixed by writing run.md with the matching AgentRun id."
---

# Check: okf-parser revela que o run.md ainda nao existia

Confirma na pratica a instrucao do proprio scaffold: sem `run.md`, toda
leitura/goal/decisao/evidencia fica com uma foreign key orfa. Corrigido
escrevendo `run.md` com `id: "2026-09-16-exciting-mccarthy-0iuk22"`.
