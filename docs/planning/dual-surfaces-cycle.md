# Ciclo de produto: duas superfícies públicas

## Decisão

O CausaGanha passa a orientar o próximo ciclo de produto por duas superfícies públicas sobre o mesmo núcleo semântico:

1. **MCP — superfície primária para agentes.** É a forma principal de fazer os dados preservados e reconciliados entrarem em uso efetivo por assistentes e automações. Um agente deve conseguir descobrir, apenas pelo catálogo MCP, como consultar processo, publicações, estado e teor sem conhecer Parquet, DuckDB, Internet Archive, manifests ou nomes internos de pipelines.
2. **Site — superfície humana.** Deve ser direto, rápido e prático: partir de CNJ, OAB, parte ou texto e conduzir a pessoa de pergunta → evidência → próxima ação, preservando provenance, freshness e limites de cobertura.

MCP e site não são produtos paralelos. São duas projeções do mesmo produto e devem compartilhar vocabulário, contratos e semântica sempre que isso for legítimo.

## Norte do ciclo

O ciclo termina quando dois testes passam.

### Teste do agente

Um agente sem conhecimento prévio do repositório recebe somente o catálogo MCP e consegue:

- descobrir a tool correta para consultar um CNJ;
- localizar publicações por CNJ/OAB/parte/texto;
- localizar decisões/acórdãos quando a pergunta depende de teor;
- distinguir arquivo, estado e teor;
- entender quando um resultado é snapshot, live, ausente, indisponível ou limitado por cobertura;
- seguir `next_actions` sem conhecer topologia interna;
- citar/prover a origem dos fatos retornados.

### Teste humano

Uma pessoa abre o site e consegue, sem ler documentação técnica:

- consultar um CNJ ou pesquisar publicações;
- entender rapidamente o que foi encontrado e de quando é;
- atravessar publicação → dossiê e dossiê → publicação/teor;
- compartilhar a consulta por URL reproduzível;
- entender um resultado vazio sem confundir “não encontrado” com “não existe”.

## Princípios de arquitetura

### Um núcleo, duas projeções

O contrato público é orientado ao domínio. O transporte e o armazenamento ficam abaixo dessa fronteira.

```text
fontes oficiais + arquivo público
        ↓
Parquet / manifests / catálogo
        ↓
adaptador semântico / contratos do domínio
        ↓
┌──────────────────┬──────────────────┐
│ MCP para agentes │ Site para humanos│
└──────────────────┴──────────────────┘
```

Conceitos comuns — processo, publicação, evidência, fonte, natureza (`arquivo`, `estado`, `teor`), freshness, limitações e próximas ações — não devem ganhar definições independentes em cada superfície.

### Infraestrutura não é UX

Detalhes como `indice_processual.parquet`, item names do Internet Archive, `loaded_remote`, `manifest_local`, partições ou schemas DuckDB podem aparecer em diagnóstico operacional, mas não como conhecimento exigido do usuário ou do agente.

### Proveniência continua obrigatória

Conveniência não autoriza fundir evidências heterogêneas. O produto deve conseguir dizer, por exemplo:

- “DataJud registra movimento X em Y”;
- “DJEN preservou publicação Z em W”;
- “JURIS/STJ contém documento que afirma Q”.

Nenhuma superfície deve transformar essas três proposições numa afirmação sintética sem origem verificável.

## Pilhas irmãs deste ciclo

A execução é intencionalmente dividida em duas stacks. Elas compartilham o contrato do produto, mas não criam dependência artificial entre código Python/MCP e frontend.

### Stack MCP — prioridade

1. **#942 — ciclo e contrato do produto.** Esta PR fixa o norte e os critérios de sucesso.
2. **#943 — catálogo orientado a jobs.** Congela por teste a experiência de seleção das tools sem conhecimento do repositório.
3. **#944 — composição explícita do dossiê.** `processo_consultar` passa a devolver próximas ações para estado live e publicações sem executar outra fonte implicitamente.
4. **#945 — descoberta de datasets de teor.** JURIS é derivado do manifest publicado; STJ permanece uma autoridade distinta.
5. **#947 — orçamento da busca temática.** Busca JURIS exige período e não pode abrir o histórico inteiro de Parquets.
6. **#948 — serviço de busca de teor.** JURIS/STJ são consultados e normalizados preservando a origem e isolando falhas parciais.
7. **#949 — `decisoes_buscar`.** A busca de teor vira uma tool de produto e completa a navegação explícita arquivo → estado → teor.

### Stack site — reaproveitada

A superfície humana já tinha uma sequência coerente aberta e não deve ser duplicada:

1. **#911 — `Minhas consultas` local-first.** Conveniência recorrente sem conta nem backend pessoal.
2. **#912 — dossiê por CNJ acionável.** Resultado deixa de ser relatório passivo e passa a oferecer próximas ações.
3. **#913 — publicação → dossiê.** Um resultado DJEN com CNJ leva ao contexto multi-fonte em um clique.

Essa stack nasceu sobre uma cadeia anterior de repaginação. Ela deve ser reconciliada causalmente com `main`, preservando somente o delta útil; retargetar cegamente e reapresentar mudanças já absorvidas não é aceitável.

### Convergência

O último degrau do ciclo é uma prova end-to-end compartilhada, baseada em #909 e #914:

- golden cases determinísticos quando úteis;
- agent experience usando somente catálogo MCP;
- fluxo humano CNJ → dossiê → publicação/documento e publicação → dossiê;
- desktop/mobile/teclado nas superfícies humanas;
- ausência, indisponibilidade e cobertura incompleta semanticamente distintas nas duas superfícies.

A fixture pode ser compartilhada como evidência, mas não vira uma segunda ontologia do produto.

## O que fica fora deste ciclo

- expansão do Lab/segmentador que não desbloqueie uma das duas superfícies;
- novas abstrações de infraestrutura sem consumidor concreto;
- novas tools MCP que apenas espelhem pipelines;
- login/conta para o site;
- esconder lacunas de cobertura em nome de uma experiência “limpa”.

## Regra de priorização

Quando houver disputa entre uma melhoria horizontal e um problema observado no uso real, vence o problema que impede agente ou pessoa de concluir um job do produto.

O ciclo deve reduzir continuamente a distância entre **dados já preservados** e **dados efetivamente usados**.
