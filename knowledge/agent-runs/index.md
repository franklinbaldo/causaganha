# Agent runs

> **Legacy histórico.** O loop horário do CausaGanha migrou para WikiSkill. Não crie novos `AgentRun`, `AgentReading`, `AgentGoal`, `AgentDecision`, `AgentEvidence` ou `AgentCheck` aqui. Consulte `.claude/hourly-loop.md` para o entrypoint atual.

Este diretório preserva as rodadas produzidas pelo mecanismo anterior, uma por `<run-id>/`, com o `AgentRun` tipado e seus documentos auxiliares (`readings/`, `goals/`, `decisions/`, `evidence/`, `checks/`). O histórico continua útil como evidência e pode ser consultado por futuras sessões Wiki, mas não é mais o formato operacional de novas rodadas.

`scripts/check_agent_run_completeness.py` permanece como validador do acervo legado enquanto esses contratos fizerem parte do bundle do CausaGanha:

```bash
uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs
```

`uv run okf-parser check knowledge --relational-schema okf.schema.sql` continua validando a integridade estrutural do bundle histórico. A retirada dos schemas/checks `Agent*` deve ocorrer separadamente, quando não houver mais consumidores que dependam deles; a migração do loop não exige reescrever ou converter mecanicamente o histórico.
