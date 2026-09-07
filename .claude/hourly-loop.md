# CausaGanha hourly loop

O loop horário do CausaGanha é operado pelo Wisk. Não reproduza aqui a política de `AgentRun`, a seleção manual de papéis ou o ciclo Experience → Wiki → Skill: isso pertence ao runtime do Wisk.

Cada checkout deve inicializar o bundle gerenciado de forma idempotente e então pedir ao Wisk a próxima sessão útil:

```bash
uvx wisk init .
uvx wisk session start-next "Faça o melhor avanço possível neste repositório"
```

Siga o `SessionType`, `RunSpec`, contexto, cadência, checks, handoffs e demais contratos selecionados pelo Wisk até o maior avanço razoável desta rodada. O estado atual do repositório e do GitHub continua sendo a fonte factual de verdade para o trabalho de domínio.

O `wisk init .` é deliberadamente não destrutivo e pode ser repetido em checkouts frescos. O estado gerenciado reproduzível fica ignorado pelo Git; conhecimento local e estado aprendido produzido pelo runtime permanecem versionáveis sob `.wikiskill/knowledge/` conforme o contrato do Wisk.

## Migração do loop legado

`knowledge/agent-runs/`, `.claude/agent-run-scaffold.md` e os tipos `AgentRun`/`AgentReading`/`AgentGoal`/`AgentDecision`/`AgentEvidence`/`AgentCheck` são legado histórico do mecanismo anterior. Preserve-os para auditoria e compatibilidade com o conhecimento já registrado, mas não crie novos AgentRuns no loop horário.

Novas rodadas devem usar exclusivamente o runtime do Wisk. Se o golden path do Wisk não conseguir representar uma necessidade recorrente do CausaGanha, prefira especializar `SessionType`/`RunSpec` em `.wikiskill/knowledge/local/` ou corrigir o próprio `franklinbaldo/wisk` em vez de recriar um segundo orquestrador local.
