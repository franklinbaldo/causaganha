# CausaGanha hourly loop

O loop horário do CausaGanha é operado exclusivamente pelo Wisk. Não reproduza aqui a política de `AgentRun`, a seleção manual de papéis ou o ciclo Experience → Wiki → Skill: isso pertence ao runtime do Wisk.

O Wisk é uma dependência de desenvolvimento do próprio projeto. Prepare o ambiente com `uv` e use sempre a instalação do projeto; não baixe ou execute outra cópia do runtime por `uvx`.

Em um checkout novo ou ainda não inicializado:

```bash
uv sync --group dev
uv run wisk init .
```

A inicialização acontece uma vez por checkout. Depois disso, cada rodada do loop horário deve executar somente o golden path do Wisk:

```bash
uv run wisk start
```

Não repita `wisk init` a cada rodada e não selecione manualmente `SessionType` ou `RunSpec` no scheduler normal. O `wisk start` deve retomar um LoopRun compatível ainda vivo ou selecionar o próximo trabalho elegível a partir da cadência, dos handoffs e do estado persistido.

Siga o `state`, `next`, `SessionType`, `RunSpec`, contexto, checks, handoffs e demais contratos retornados pelo Wisk até o maior avanço razoável da rodada. O estado atual do repositório e do GitHub continua sendo a fonte factual de verdade para o trabalho de domínio.

O estado gerenciado e aprendido do runtime pertence ao namespace `.wisk/`. Conhecimento local e especializações do consumidor devem usar `.wisk/knowledge/local/`. Não introduza novos caminhos, prompts ou contratos sob o nome antigo do projeto.

## Migração do loop legado

`knowledge/agent-runs/`, `.claude/agent-run-scaffold.md` e os tipos `AgentRun`/`AgentReading`/`AgentGoal`/`AgentDecision`/`AgentEvidence`/`AgentCheck` são legado histórico do mecanismo anterior. Preserve-os para auditoria e compatibilidade com o conhecimento já registrado, mas não crie novos AgentRuns no loop horário.

Novas rodadas devem usar exclusivamente o runtime do Wisk. Se o golden path do Wisk não conseguir representar uma necessidade recorrente do CausaGanha, prefira especializar `SessionType`/`RunSpec` em `.wisk/knowledge/local/` ou corrigir o próprio `franklinbaldo/wisk` em vez de recriar um segundo orquestrador local.


## Estado durável, OKF e custo administrativo

O loop deve minimizar estado implícito e reconstrução repetitiva. Quando uma necessidade de memória operacional realmente precisar sobreviver a fresh checkout — blocker, condição de reativação, decisão estável, objetivo atual, próxima ação, evidência, PR/issue ativa — represente-a em OKF no repositório e consuma-a com o `okf-parser` na versão mais atual compatível disponível.

Antes de criar novo schema, parser, registry, JSON/YAML paralelo, checklist próprio ou formato de tracking, verifique primeiro se o `okf-parser` já cobre o caso. Atualizar a dependência para uma versão mais recente compatível faz parte da manutenção quando isso eliminar duplicação ou habilitar o contrato necessário.

Não transforme cada execução em um artefato de bookkeeping. Estado novo só deve ser persistido quando houver conhecimento material novo.

## Regra anti-PR cerimonial

Não abra PR exclusivamente para:

- confirmar que outra PR já foi mergeada;
- `close out round`;
- `round report`;
- copiar para Git o fato de que um run terminou;
- reconfirmar um blocker externo inalterado;
- registrar bookkeeping do Wisk sem mudança material de produto, dados, evidência ou conhecimento.

Quando uma rodada tiver uma PR material, persista junto dela o estado Wisk/OKF que realmente mudou. Quando não houver mudança material, feche o run no estado canônico existente sem criar uma PR adicional.

Se um blocker externo persistir — por exemplo credencial ausente, deploy que depende de ação humana ou acesso indisponível — registre uma única vez o estado `blocked`, a evidência, a condição exata de reativação e a próxima ação necessária. Não revalide nem recommite o mesmo blocker a cada hora sem sinal novo de desbloqueio.

Uma boa rodada deve terminar preferencialmente com trabalho material entregue/mergeado, dívida real reduzida ou blocker novo concretamente estreitado; nunca apenas com mais metabolismo administrativo.
