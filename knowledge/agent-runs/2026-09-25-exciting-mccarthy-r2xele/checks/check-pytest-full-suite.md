---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-r2xele-check-pytest-full-suite"
run_id: "2026-09-25-exciting-mccarthy-r2xele"
command: "uv run pytest -q"
result: "passed"
summary: "Suite completa do repositorio (1918 testes, 1 skip) 100% verde apos preencher completed_at/primary_goal_id/result_summary/next_move deste run.md. Confirma a nota do proprio scaffold: com o relatorio ainda em rascunho (campos vazios), tests/test_check_agent_run_completeness.py e os dois testes de paridade Zod/domain-model (tests/web/test_generate_okf_zod_schemas.py, tests/causaganha_mcp/test_okf_domain_models.py) teriam falhado pela mesma causa (a forma do AgentRun incompleto no bundle); preenchido o relatorio, os tres passam sem nenhuma regeneracao de arquivo gerado."
---

# Check: pytest -q (suite completa do repositorio)

```
$ uv run pytest -q
........................................................................ [  3%]
...
...................................s.................................... [ 71%]
...
...............................................                          [100%]
$ echo $?
0
```

1918 testes coletados, 1 skip, 0 falhas.
