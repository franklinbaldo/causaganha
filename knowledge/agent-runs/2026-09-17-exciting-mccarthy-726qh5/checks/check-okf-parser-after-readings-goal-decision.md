---
type: AgentCheck
id: "2026-09-17-exciting-mccarthy-726qh5-check-okf-parser-after-readings-goal-decision"
run_id: "2026-09-17-exciting-mccarthy-726qh5"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "pass"
evidence_id: ""
---

# Check: okf-parser apos leituras, goal e decisao

Rodado apos preencher as quatro `AgentReading`, a `AgentGoal`
`goal-djen-sample-batch18` e a `AgentDecision`
`decision-avoid-pr1574-collision`, e apos preencher o `id` do proprio
`AgentRun` (a chave de FK que os `AgentReading` referenciam). Resultado:
`conformant: true`, `diagnostics: []`, `concept_count: 1978`. A
primeira tentativa (antes de preencher o `id` do AgentRun) reportou 4
erros `OKF022` de foreign key -- corrigidos preenchendo `run.md`'s
frontmatter (`id`, `started_at`, `branch_at_start`, `commit_at_start`,
as quatro `*_reading_id`, `goal_ids`/`primary_goal_id`,
`considered_work`, `selected_work`, `expected_behavior`,
`decision_ids`) em vez de deixar o scaffold com campos vazios.
