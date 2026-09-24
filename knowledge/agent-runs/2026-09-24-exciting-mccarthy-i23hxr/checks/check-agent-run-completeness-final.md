---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-i23hxr-check-agent-run-completeness-final"
run_id: "2026-09-24-exciting-mccarthy-i23hxr"
command: "uv run pytest -q tests/test_check_agent_run_completeness.py tests/web/test_generate_okf_zod_schemas.py tests/causaganha_mcp/test_okf_domain_models.py"
result: "passed"
evidence_id: "2026-09-24-exciting-mccarthy-i23hxr-evidence-repair-script-and-green"
summary: "Os 3 testes voltam a GREEN apos run.md ser preenchido e o AgentGoal deste run ser corrigido para os nomes de campo reais do schema (goal/rationale/status, nao statement/motivation)."
---

# Check: os 3 testes sensiveis a rascunho, pos-preenchimento

A propria suite completa desta rodada (rodada em background antes do
commit) mostrou exatamente 2 dessas 3 falhas -- causadas apenas por
`run.md` ainda estar em rascunho (`completed_at` vazio) no momento em
que rodou. Reverificado apos preencher `completed_at`/`result_summary`/
`next_move`.
