# CausaGanha hourly loop

O loop horário do CausaGanha é operado exclusivamente pelo Wisk. Não reproduza aqui a política de `AgentRun`, a seleção manual de papéis ou o ciclo Experience → Wiki → Skill: isso pertence ao runtime do Wisk.

O Wisk é uma dependência de desenvolvimento do próprio projeto. Prepare o ambiente com `uv` e use sempre a instalação do projeto; não baixe ou execute outra cópia do runtime por `uvx`.

Em um checkout novo ou ainda não inicializado:

```bash
uv sync --group dev
uv run wisk init .
```

A inicialização é bootstrap idempotente, não uma etapa conceitual de cada rodada. Depois disso, cada execução deve entrar no golden path do Wisk usando a instalação do ambiente:

```bash
uv run wisk session start-next "Faça o melhor avanço possível neste repositório"
```

Enquanto a versão instalada ainda expuser `session start-next`, use esse comando de compatibilidade. Assim que a versão do Wisk que implementa o RFC 0006 estiver publicada e adotada pelo projeto, o loop deve reduzir-se a:

```bash
uv run wisk start
```

Siga o `SessionType`, `RunSpec`, contexto, cadência, checks, handoffs e demais contratos selecionados pelo Wisk até o maior avanço razoável da rodada. O estado atual do repositório e do GitHub continua sendo a fonte factual de verdade para o trabalho de domínio.

O estado gerenciado e aprendido do runtime pertence ao namespace `.wisk/`. Conhecimento local e especializações do consumidor devem usar `.wisk/knowledge/local/`. Não introduza novos caminhos, prompts ou contratos sob o nome antigo do projeto.

## Migração do loop legado

`knowledge/agent-runs/`, `.claude/agent-run-scaffold.md` e os tipos `AgentRun`/`AgentReading`/`AgentGoal`/`AgentDecision`/`AgentEvidence`/`AgentCheck` são legado histórico do mecanismo anterior. Preserve-os para auditoria e compatibilidade com o conhecimento já registrado, mas não crie novos AgentRuns no loop horário.

Novas rodadas devem usar exclusivamente o runtime do Wisk. Se o golden path do Wisk não conseguir representar uma necessidade recorrente do CausaGanha, prefira especializar `SessionType`/`RunSpec` em `.wisk/knowledge/local/` ou corrigir o próprio `franklinbaldo/wisk` em vez de recriar um segundo orquestrador local.
