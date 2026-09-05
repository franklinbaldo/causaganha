# CausaGanha hourly loop

A primeira ação de cada rodada é copiar `.claude/agent-run-scaffold.md` para `knowledge/agent-runs/<run-id>/run.md`.

O `AgentRun` é o roteiro operacional da sessão. Ele nasce incompleto e amadurece junto com o trabalho.

Rode repetidamente:

```bash
uv run okf-parser check knowledge --relational-schema okf.schema.sql
```

Use a validação como feedback operacional: observe o que o contrato ainda pede, faça o trabalho correspondente, registre o resultado em OKF tipado e valide novamente.

## Abrir a rodada

Materialize primeiro as leituras requeridas como `AgentReading`:

- `CLAUDE.md`;
- issues abertas relevantes;
- PRs em andamento;
- conhecimento OKF relevante.

Cada leitura registra a referência consultada e o achado que ela trouxe para a decisão da sessão. Ligue seus IDs aos campos `*_reading_id` do `AgentRun`.

Depois crie um ou mais `AgentGoal`. Cada goal declara o que se pretende avançar, por que isso importa e qual sinal observável permitirá dizer que houve avanço. Registre os IDs em `goal_ids` e escolha `primary_goal_id`.

Leia o estado real do repositório, compare alternativas em `considered_work`, escolha o trabalho e declare `expected_behavior`, `entry_state` e `target_state`.

## Avançar a rodada

Use TDD como fluxo padrão: issue/oportunidade → PR RED → GREEN → revisão → merge.

Registre escolhas relevantes como `AgentDecision`. Registre provas concretas como `AgentEvidence`: teste RED, teste GREEN, diff, CI, runtime, issue, PR, review ou conhecimento OKF. Registre verificações executadas como `AgentCheck`, preferencialmente ligando cada check à evidência que demonstra seu resultado.

O relatório deve refletir o trabalho enquanto ele acontece. Atualize `decision_ids`, `evidence_ids` e `check_ids` e rode o check do `okf-parser` após avanços materiais.

Priorize continuidade de PRs e trabalho já iniciado. O estado real do projeto e o contrato OKF orientam qual avanço faz mais sentido em cada rodada.

Types, specs e schemas são parte viva da arquitetura. Crie ou evolua esses contratos quando isso tornar o modelo mais correto, simples ou expressivo, incluindo migrações e testes correspondentes.

## Fechar a rodada

Finalize `completed_at`, `result_state`, `result_summary` e `next_move`, atualize o estado dos `AgentGoal` e rode novamente o check do `okf-parser`.

Uma rodada bem representada permite reconstruir: o que foi lido, quais goals orientaram a sessão, quais decisões foram tomadas, quais evidências sustentam o avanço, quais checks foram executados, qual estado foi alcançado e qual próximo movimento ficou disponível.

A próxima rodada lê os relatórios anteriores e o estado atual do GitHub, cria um novo scaffold e continua a evolução do CausaGanha.
