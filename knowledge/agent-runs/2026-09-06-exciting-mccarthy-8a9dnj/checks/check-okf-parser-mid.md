---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-8a9dnj-check-okf-parser-mid"
run_id: "2026-09-06-exciting-mccarthy-8a9dnj"
goal_id: "2026-09-06-exciting-mccarthy-8a9dnj-goal-copy-link-coverage"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "observed"
evidence_id: "2026-09-06-exciting-mccarthy-8a9dnj-evidence-diff"
summary: "Run mid-round, before run.md's placeholder id (\"\") was filled in: 9 OKF022 foreign-key diagnostics, each an AgentReading/AgentGoal/AgentDecision/AgentEvidence file whose run_id ('2026-09-06-exciting-mccarthy-8a9dnj') had no matching AgentRun row yet, since run.md still carried the scaffold's empty id. Confirms the scaffold's own stated mechanism ('deliberadamente inválido ao nascer') — used this failure to drive completing run.md's frontmatter next, then re-ran the check (see check-web-suite's sibling final check) to confirm it clears."
---

# Check: okf-parser em meio à rodada, lacuna esperada do scaffold

9 diagnósticos de FK ausente, todos porque `run.md` ainda tinha `id: ""` do scaffold. Confirma o mecanismo do próprio scaffold — corrigido a seguir preenchendo o frontmatter de `run.md`.
