---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-fipj1n-check-okf-parser-after-merge"
run_id: "2026-09-25-exciting-mccarthy-fipj1n"
goal_id: "2026-09-25-exciting-mccarthy-fipj1n-goal-juris-manifest-mes-ano-validation"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "Rodado após PR #1646 mesclada (sha 44c2f24) e run.md atualizado com result_state=merged. conformant=true, 0 diagnostics, concept_count=2378, markdown_count=2381."
---

# Check: okf-parser (após merge)

`uv run okf-parser check knowledge --relational-schema okf.schema.sql`
segue `conformant: true`, 0 diagnostics, após `run.md` desta rodada ser
atualizado com o resultado final (`result_state: merged`, sha da mesclagem
de `PR #1646`).
