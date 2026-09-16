---
type: AgentCheck
id: "2026-09-16-exciting-mccarthy-uyx7xc-check-okf-parser-after-readings-goal-decision"
run_id: "2026-09-16-exciting-mccarthy-uyx7xc"
goal_id: "2026-09-16-exciting-mccarthy-uyx7xc-goal-djen-sample-batch3"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "conformant: true, 0 diagnostics, concept_count=1773, markdown_count=1776, reserved_count=3 -- run after the 4 initial AgentReading files, the AgentGoal and the AgentDecision were written."
---

# Check: okf-parser apos leituras, goal e decisao

Rodado apos criar as 4 leituras iniciais (`claude_md`, `issues`, `prs`,
`okf_knowledge`), o `AgentGoal` `goal-djen-sample-batch3` e o
`AgentDecision` `decision-predecode-html-entities`. Bundle conformante,
sem diagnosticos.
