# CausaGanha hourly loop

A primeira ação de cada rodada é copiar `.claude/agent-run-scaffold.md` para `knowledge/agent-runs/<timestamp>-<slug>.md`.

O `AgentRun` é o roteiro operacional da sessão. Rode repetidamente:

```bash
uv run okf-parser check knowledge --relational-schema okf.schema.sql
```

Use as falhas de validação para orientar o próximo avanço e preencha o relatório conforme o trabalho acontece.

A rodada deve confirmar a leitura de `CLAUDE.md`, das issues abertas, dos PRs em andamento e do conhecimento OKF relevante; definir goals e sua motivação; registrar alternativas consideradas; escolher o trabalho que melhor avança o CausaGanha; declarar o comportamento esperado e os estados de entrada/alvo; produzir ações, evidências e checks; e fechar a rodada com estado resultante, resumo e próximo avanço natural.

Leia o estado real do repositório antes de decidir. Priorize continuidade de PRs e trabalho já iniciado. Use TDD como fluxo padrão: issue/oportunidade → PR RED → GREEN → revisão → merge.

Types, specs e schemas fazem parte viva da arquitetura. Crie ou evolua esses contratos quando isso tornar o modelo mais correto, simples ou expressivo, incluindo as migrações e os testes correspondentes.

O relatório acompanha a rodada inteira: nasce incompleto, amadurece junto com o trabalho e termina representando fielmente o estado alcançado. A próxima rodada deve conseguir se orientar pelos relatórios anteriores e pelo estado atual do GitHub.
