---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-ejibsp-check-completeness-over-real-tree"
run_id: "2026-09-05-exciting-mccarthy-ejibsp"
goal_id: "2026-09-05-exciting-mccarthy-ejibsp-goal-extend-completeness-checker"
command: "uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs"
result: "passed"
evidence_id: "2026-09-05-exciting-mccarthy-ejibsp-evidence-index-md-crash-fix"
summary: "First run crashed with DocumentParseError on knowledge/agent-runs/index.md; fixed by skipping frontmatter-less files in directory mode; second run: exit 0, all 38 Agent*-typed documents across both rounds report complete."
---

# Check: checador de completude sobre a árvore real (com crash real encontrado e corrigido)
