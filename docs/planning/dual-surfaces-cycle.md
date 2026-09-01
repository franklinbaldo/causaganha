# Ciclo de produto: duas superfícies públicas

## Decisão

O CausaGanha passa a orientar o próximo ciclo de produto por duas superfícies públicas sobre o mesmo núcleo semântico:

1. **MCP — superfície primária para agentes.** É a forma principal de fazer os dados preservados e reconciliados entrarem em uso efetivo por assistentes e automações. Um agente deve conseguir descobrir, apenas pelo catálogo MCP, como consultar processo, publicações, estado e teor sem conhecer Parquet, DuckDB, Internet Archive, manifests ou nomes internos de pipelines.
2. **Site — superfície humana.** Deve ser direto, rápido e prático: partir de CNJ, OAB, parte ou texto e conduzir a pessoa de pergunta → evidência → próxima ação, preservando provenance, freshness e limites de cobertura.

MCP e site não são produtos paralelos. São duas projeções do mesmo produto e devem compartilhar vocabulário, contratos e semântica sempre que isso for legítimo.

## Norte do ciclo

O ciclo termina quando dois testes passam:

### Teste do agente

Um agente sem conhecimento prévio do repositório recebe somente o catálogo MCP e consegue:

- descobrir a tool correta para consultar um CNJ;
- localizar publicações por CNJ/OAB/parte/texto;
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

## Pilha deste ciclo

Esta mudança é a base de uma pilha de PRs, não uma entrega monolítica.

### PR 1 — ciclo e contrato de produto

Este documento fixa o norte, os testes de sucesso e a ordem de execução. Ele consolida, sem duplicar, o que já está espalhado por #904, #914 e issues filhas.

### PR 2 — MCP orientado a jobs

Reorganizar a apresentação/instruções do MCP para que tools de produto sejam primeira classe e tools `*_status` sejam claramente operacionais. Descrições precisam dizer quando usar, quando não usar e como compor as tools. Base: #914 e #891.

### PR 3 — MCP: busca de teor

Adicionar a superfície de produto para localizar decisões/documentos JURIS/STJ por job, sem exigir que o agente conheça schemas de origem. Base: #918.

### PR 4 — site: dossiê acionável

Transformar `/processo` em ponto de decisão: ações para publicações, teor, permalink e explicação de cobertura/freshness. Base: #905 e #907.

### PR 5 — site: publicação → processo

Tornar o caminho publicação → dossiê explícito e reproduzível; preservar filtros e permalink e melhorar reutilização da busca. Base: #906.

### PR 6 — prova end-to-end das duas superfícies

Adicionar golden cases determinísticos e uma avaliação de agent experience do MCP, além de Playwright dos fluxos humanos relevantes. O objetivo é detectar regressões de utilidade, não apenas schema quebrado ou screenshot estático. Base: #909 e critérios de #914.

## O que fica fora deste ciclo

- expansão do Lab/segmentador que não desbloqueie uma das duas superfícies;
- novas abstrações de infraestrutura sem consumidor concreto;
- novas tools MCP que apenas espelhem pipelines;
- login/conta para o site;
- esconder lacunas de cobertura em nome de uma experiência “limpa”.

`Minhas consultas` (#908) continua valiosa, mas vem depois do caminho principal CNJ/publicações estar redondo.

## Regra de priorização

Quando houver disputa entre uma melhoria horizontal e um problema observado no uso real, vence o problema que impede agente ou pessoa de concluir um job do produto.

O ciclo deve reduzir continuamente a distância entre **dados já preservados** e **dados efetivamente usados**.
