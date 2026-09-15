---
type: AgentCheck
id: "2026-09-15-exciting-mccarthy-yz281l-check-okf-parser-final"
run_id: "2026-09-15-exciting-mccarthy-yz281l"
goal_id: "2026-09-15-exciting-mccarthy-yz281l-goal-row-group-size-a1b"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: "2026-09-15-exciting-mccarthy-yz281l-evidence-green-test"
summary: "Após preencher run.md (completed_at, evidence_ids finais, decision_ids, result_summary, next_move), okf-parser check retorna conformant=true, 0 diagnostics, concept_count=1353. Bundle knowledge/ íntegro com esta rodada completa: 4 readings, 1 goal (achieved), 2 decisions, 4 evidence, 3 checks (contando este)."
---

# Check final: okf-parser

`uv run okf-parser check knowledge --relational-schema okf.schema.sql` → `conformant: true`, `0 diagnostics`, `concept_count: 1353`. Bundle íntegro com `run.md` completo (todos os campos preenchidos, todos os IDs referenciados existem). Próximo passo: confirmar `uv run pytest -q` volta a ficar totalmente verde (a cascata de `test_check_agent_run_completeness` deve desaparecer agora que `run.md` está completo) e então commitar/push/abrir PR.
