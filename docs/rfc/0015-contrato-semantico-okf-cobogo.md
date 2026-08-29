# RFC 0015 — Contrato semântico do produto com OKF e apresentação Cobogó

- **Status:** Proposto
- **Data:** 2026-08-29
- **Depende de:** RFC 0005 (processo como recurso central), RFC 0009 (camada de dados da Web), RFC 0014 (MCP como superfície de produto)
- **Complementa:** o bundle `knowledge/` e seus contratos relacionais já validados por `okf-parser`
- **Escopo:** modelo semântico público do CausaGanha, fronteira entre dados e produto e regras para a nova Web baseada em Cobogó

## 1. Resumo executivo

O CausaGanha já possui três decisões arquiteturais corretas, mas ainda não possui uma fronteira única entre elas:

1. o **processo judicial**, identificado pelo CNJ, é o recurso central do produto (RFC 0005);
2. os **Parquets canônicos, manifests e índices finos** são o plano de dados, consultado com DuckDB/DuckDB-WASM, sem uma tabela larga paralela como segunda fonte de verdade (RFC 0005 e RFC 0009);
3. o **MCP** começou a expor tarefas de produto, como consultar processo e buscar publicações, escondendo do agente detalhes de partições, joins e transporte (RFC 0014 e implementações posteriores).

Falta um contrato que diga, de forma independente de armazenamento, protocolo ou interface visual, **o que é um processo, uma publicação, um evento, um documento, um advogado, um órgão judicial e a proveniência de cada afirmação**.

Esta RFC decide que:

- **OKF v0.2 é o contrato semântico canônico do produto**;
- **`okf-parser` é o mecanismo de leitura, inspeção e validação desse contrato**;
- **Parquet/DuckDB continuam sendo o plano canônico de dados e consulta**;
- **Cobogó é a camada de apresentação da nova Web**;
- Web, MCP e futuras exportações devem derivar suas representações do mesmo modelo semântico, em vez de reconstruir conceitos diretamente a partir de rows, SQL ou componentes de UI.

Em forma curta:

```text
fontes oficiais / arquivo
        ↓
Parquet + manifests + índices       plano de dados
        ↓
adaptadores de domínio
        ↓
OKF + contratos validados           plano semântico
        ↓
projeções orientadas à tarefa
        ↓
Web/Cobogó | MCP | exportações      superfícies de produto
```

**OKF é canônico para o significado; Parquet é canônico para os registros.** Não há conflito entre as duas afirmações porque elas governam planos diferentes.

## 2. Problema

A Web atual acumulou conhecimento de domínio em vários lugares ao mesmo tempo: SQL/query contracts, loaders, tipos TypeScript, componentes Svelte/Astro, textos explicativos e regras específicas de cada página. O MCP, por sua vez, possui seus próprios modelos de retorno. Isso cria quatro problemas.

### 2.1. Semântica duplicada

Uma mesma ideia — por exemplo, “esta publicação pertence a este processo e veio do DJEN” — pode ser reconstruída de modos diferentes pela Web e pelo MCP. Se cada consumidor define seus próprios campos, nulabilidade, identidade e regras de reconciliação, a divergência é apenas uma questão de tempo.

### 2.2. Acoplamento entre produto e armazenamento

DuckDB, Parquet, nomes de arquivos e partições são excelentes mecanismos de consulta. Não devem, porém, definir a linguagem pública do produto. Uma página de processo não deveria precisar saber se um evento veio de uma row de `comunicacoes`, de um índice fino ou de uma view temporária para decidir o que significa “publicação”.

### 2.3. Proveniência tratada como detalhe de implementação

No CausaGanha, a origem de um dado é parte do próprio dado. DJEN, DataJud, TJRO JURIS e STJ podem registrar aspectos diferentes — ou aparentemente conflitantes — do mesmo processo. Uma camada de apresentação que recebe apenas valores já achatados perde a capacidade de dizer de onde cada afirmação veio.

### 2.4. A interface virou uma segunda arquitetura

A Web passou a expor detalhes como DuckDB-WASM, Parquets, estado de coleta e outras preocupações operacionais antes de responder à pergunta do usuário. Isso contradiz a própria diretriz do frontend de evitar “appification” de tarefas de leitura. A reconstrução da Web precisa tornar a UI uma projeção do produto, não um mapa da infraestrutura.

## 3. Decisão arquitetural

### 3.1. O bundle OKF existente passa a governar também o vocabulário público

O repositório já usa `knowledge/` para fatos e contratos estáveis do projeto. O bundle atualmente modela fontes e pipelines e deixa explicitamente os datasets judiciais no plano Parquet/DuckDB. Esta RFC **estende esse desenho**, não o substitui.

O bundle passa a conter, além dos conceitos operacionais já existentes, os conceitos e contratos que definem a linguagem pública do produto. `okf-parser` continua sendo a autoridade de validação relacional desse conhecimento.

A adoção deve usar a fronteira já prevista pelo próprio `okf-parser`: fontes externas são adaptadas por uma política explícita, com proveniência, para uma representação OKF canônica; consumidores posteriores não aprendem individualmente cada dialeto de origem.

### 3.2. OKF não vira banco de dados judicial

Esta RFC **não** manda converter milhões de publicações ou processos em milhões de arquivos Markdown.

O bundle versionado contém:

- vocabulário e contratos do domínio;
- relações entre conceitos estáveis;
- documentação semântica;
- fixtures representativas necessárias para validar o mapeamento.

Os registros em massa continuam em Parquet e são localizados pelos manifests, catálogo e índices existentes. Uma consulta pode produzir uma **projeção semântica transitória** de um processo ou conjunto de publicações conforme o contrato OKF, sem materializar essa projeção como novo corpus persistente.

Esta distinção é normativa: uma implementação que mantenha uma cópia OKF persistente de todo o acervo como nova fonte de verdade viola esta RFC.

### 3.3. O adaptador é a única fronteira que conhece os dois mundos

Será criada uma camada de domínio responsável por transformar resultados canônicos de consulta em conceitos/relações do contrato semântico. Ela pode conhecer schemas Parquet e o modelo OKF. As camadas acima não podem.

```text
DuckDB row ──X──> componente Cobogó
DuckDB row ──X──> schema MCP próprio

DuckDB row ──> adaptador ──> projeção semântica ──> Cobogó/MCP
```

A regra evita que uma mudança de layout de Parquet obrigue uma mudança de UI e evita que uma mudança visual redefina o significado de um campo.

## 4. Modelo semântico mínimo

A primeira versão deve ser pequena. OKF não impõe uma taxonomia e esta RFC deliberadamente não tenta criar uma ontologia completa do processo civil brasileiro.

Os tipos iniciais são:

| Tipo | Identidade mínima | Papel no produto |
| --- | --- | --- |
| `Processo` | CNJ normalizado | recurso central e agregador verificável |
| `Publicacao` | identificador estável derivado da fonte | ato/publicação oficialmente encontrada no acervo |
| `EventoProcessual` | identidade estável no contexto da fonte | acontecimento mostrado na linha do tempo |
| `Documento` | identificador da fonte ou digest determinístico | documento ou decisão associável ao processo |
| `Pessoa` | identificador disponível e escopo explícito | pessoa que aparece como parte ou outro participante |
| `Advogado` | OAB/UF quando disponível, sem inventar identidade quando ausente | participante profissional pesquisável |
| `OrgaoJudicial` | identificador/código da fonte com origem explícita | tribunal, órgão ou unidade responsável pelo registro |
| `Fonte` | nome estável já usado no bundle | sistema ou corpus que sustenta a evidência |

`Parte` é inicialmente um **papel de uma Pessoa em um Processo**, não um novo tipo de pessoa. Da mesma forma, a RFC não cria tipos separados para autor, réu, recorrente etc.; esses papéis pertencem às relações e só serão normalizados quando houver evidência de que a normalização é estável entre fontes.

Relações mínimas a representar e validar:

```text
Publicacao      → Processo
EventoProcessual → Processo
EventoProcessual → Publicacao | Documento
Documento       → Processo
Pessoa          → Processo        [papel na fonte]
Advogado        → Processo/Pessoa [quando a fonte sustentar a representação]
OrgaoJudicial   → Publicacao/EventoProcessual
conceito        → Fonte           [proveniência]
```

Os nomes físicos dos campos e relações serão definidos nos specs/contratos OKF, não em componentes Cobogó nem em schemas MCP independentes.

## 5. Identidade

### 5.1. Processo

O identificador semântico de `Processo` é o CNJ normalizado de 20 dígitos, conforme a decisão já vigente na RFC 0005. A máscara é apresentação, nunca identidade.

### 5.2. Registros oriundos de fontes

`Publicacao`, `EventoProcessual` e `Documento` devem preferir identificadores naturais da fonte. Quando a fonte não oferecer chave estável, o adaptador pode produzir chave determinística a partir de coordenadas imutáveis do registro ou de digest documentado.

Uma posição de array, número de página da Web, ordem atual de query ou índice de lista **não** é identidade válida.

### 5.3. Pessoas e advogados

O modelo não deve alegar identidade civil que a fonte não prova. Nome igual não significa pessoa igual. OAB/UF pode identificar um advogado quando disponível; na ausência de identificador suficiente, o conceito permanece escopado à ocorrência/fonte e não é reconciliado silenciosamente com homônimos.

## 6. Proveniência, reconciliação e conflito

OKF v0.2 torna `sources` e proveniência parte estrutural do formato. O CausaGanha deve aproveitar essa semântica em vez de inventar um segundo mecanismo de “fonte” apenas para a Web.

Regras normativas:

1. toda afirmação material exibida como fato derivado de fonte externa deve ser rastreável à sua fonte;
2. `resource`/localizadores devem apontar, quando possível, para o artefato oficial ou preservado que sustenta o conceito;
3. a origem **ao vivo** e a origem **arquivada** não podem ser tratadas como equivalentes silenciosamente;
4. reconciliação agrega evidências; não apaga valores divergentes de origem;
5. um valor derivado deve distinguir a regra de projeção da evidência que a alimentou;
6. a UI pode ocultar detalhes de proveniência por progressive disclosure, mas não pode descartá-los antes da camada de apresentação.

Quando duas fontes discordarem, o contrato deve permitir transportar ambas as afirmações com suas origens. Escolher um “valor vencedor” só é permitido quando existir regra de reconciliação explícita e testável; mesmo assim, os valores de origem permanecem acessíveis.

## 7. Projeções de produto

O contrato OKF é mais rico que uma resposta de tela ou uma tool individual. Consumidores não precisam receber o grafo inteiro.

Cada tarefa pode definir uma **projeção orientada ao uso**, desde que preserve:

- identidades canônicas;
- significado dos campos;
- relações necessárias à tarefa;
- proveniência relevante;
- distinção entre ausência de registro e ausência de cobertura.

Exemplos:

```text
processo_consultar(CNJ)
    → Processo + participantes + eventos + publicações + documentos + fontes

publicacoes_buscar(...)
    → Publicacao[] + Processo? + Advogado/Pessoa? + fontes + paginação

/p/{CNJ}
    → a mesma projeção semântica de processo, apresentada por Cobogó
```

A serialização concreta pode ser JSON para transporte. **JSON não é o contrato semântico**; é apenas uma serialização de uma projeção cujo significado vem do modelo OKF.

## 8. Web nova: Cobogó como apresentação

Cobogó é adotado como camada visual da nova Web. Ele deve receber modelos já semânticos e não incorporar conhecimento de armazenamento.

### 8.1. Regra de dependência

Componentes de apresentação podem conhecer `Processo`, `Publicacao`, `EventoProcessual` e demais projeções de produto. Não podem conhecer:

- nomes de arquivos Parquet;
- partições por ano/tribunal;
- SQL de reconciliação;
- rows DuckDB cruas;
- detalhes do manifest necessários apenas para localizar dados.

O padrão desejado é:

```text
consulta → adaptador → ProcessoView → componente Cobogó
```

Não:

```text
consulta → row DuckDB → componente que interpreta a row
```

### 8.2. Hierarquia do produto

A nova Web deve começar pelas tarefas públicas, não pela operação do pipeline. A navegação primária é:

```text
Buscar | Publicações | Sobre os dados
```

A busca inicial pode detectar CNJ, OAB e texto e encaminhar à tarefa apropriada. A página de processo é o principal dossiê verificável. Cobertura, saúde dos pipelines, downloads, DuckDB, Internet Archive e detalhes de preservação continuam disponíveis, mas pertencem a **Sobre os dados** e à transparência, não ao caminho principal de consulta.

### 8.3. Proveniência próxima da evidência

O novo site não deve abrir com uma aula de arquitetura. A proveniência aparece junto do fato que sustenta — por exemplo, um selo ou detalhe de fonte em uma publicação ou evento — e pode expandir para metadados técnicos quando o usuário desejar auditar.

## 9. MCP e outras superfícies

A RFC 0014 estabeleceu o MCP como superfície de produto. Esta RFC endurece a fronteira: tools orientadas ao usuário devem consumir as mesmas projeções semânticas que a Web sempre que representarem a mesma tarefa.

Isso não exige respostas byte a byte idênticas. MCP pode usar uma forma compacta adequada a agentes e Web pode usar uma view adequada à leitura. O que não pode divergir é identidade, interpretação, proveniência ou regra de reconciliação.

Um agente que chama `publicacoes_buscar` não precisa saber arquivo, partição, join ou transporte. Um componente Cobogó também não.

## 10. Uso de `okf-parser`

A adoção não se limita a escrever Markdown com frontmatter. O parser faz parte do contrato de engenharia.

A implementação deve:

1. estender o bundle `knowledge/` com os tipos/contratos de domínio;
2. estender os contratos relacionais existentes para identidade, cardinalidade e referências que sejam realmente invariantes;
3. validar o bundle em CI com a versão de `okf-parser` fixada pelo projeto;
4. manter fixtures pequenas e representativas de projeções oriundas de DJEN, DataJud, TJRO JURIS e STJ;
5. testar o adaptador contra essas fixtures e contra casos de conflito/ausência parcial;
6. usar os relatórios determinísticos do parser para falhar de forma legível quando o contrato for violado.

Se uma capacidade necessária existir apenas em versão posterior do `okf-parser`, a atualização da dependência deve ser explícita e testada; esta RFC não autoriza uma faixa de versão móvel.

## 11. O que permanece no plano de dados

Esta RFC não altera as decisões de armazenamento da RFC 0005/0009.

Continuam pertencendo ao plano de dados:

- ZIPs preservados;
- Parquets canônicos;
- manifests e logs append-only;
- `indice_processual.parquet`;
- catálogo;
- DuckDB/DuckDB-WASM como motores de consulta;
- poda de partições e estratégias de join.

O adaptador semântico pode usar tudo isso. Cobogó e as tools de produto não devem depender desses detalhes diretamente.

## 12. Migração

A migração será incremental e não exige uma reescrita dos pipelines existentes.

### Fase 1 — contrato OKF mínimo

Modelar `Processo`, `Publicacao`, `EventoProcessual`, `Documento`, `Pessoa`, `Advogado` e `OrgaoJudicial`; ampliar os contratos relacionais; criar fixtures cross-fonte e testes do adaptador.

**Gate:** um CNJ representativo, com dados de mais de uma fonte quando disponíveis, é projetado e validado sem que o consumidor precise conhecer schemas físicos.

### Fase 2 — casca Cobogó e busca

Criar a nova homepage e navegação primária com Cobogó, mantendo o site estático e a busca como protagonista. A homepage não migra dashboards operacionais, calendário demonstrativo ou componentes antigos por inércia.

**Gate:** o usuário consegue iniciar busca por CNJ/texto sem exposição prévia a detalhes de armazenamento.

### Fase 3 — dossiê de processo

Reimplementar a página de processo consumindo a projeção `Processo`, com conteúdo primeiro e proveniência auditável por evento/publicação/documento.

**Gate:** nenhum componente do dossiê interpreta row DuckDB crua.

### Fase 4 — publicações

Reimplementar busca e resultados de publicações sobre a mesma semântica usada por `publicacoes_buscar` no MCP.

**Gate:** Web e MCP concordam sobre identidade, fonte e relação com processo para as mesmas fixtures.

### Fase 5 — transparência do arquivo

Reagrupar cobertura, estado de coleta, metodologia, downloads, catálogo, DuckDB e Internet Archive em **Sobre os dados**, preservando a capacidade de auditoria sem transformar infraestrutura em navegação principal.

## 13. Política para funcionalidades antigas

Uma funcionalidade existente não migra para a nova Web apenas porque já existe.

Para entrar na nova superfície ela deve responder a uma tarefa concreta do usuário e poder ser expressa sobre o contrato semântico ou ser claramente classificada como ferramenta de transparência/operação.

`advogados`, `comparador`, `explorador`, `stats`, calendários, heatmaps e atalhos globais podem continuar acessíveis durante a transição, mas não recebem automaticamente lugar na nova hierarquia. Git preserva o código anterior; a nova arquitetura não precisa preservar cada decisão visual dentro da interface.

## 14. Não objetivos

Esta RFC não pretende:

- substituir Parquet ou DuckDB por OKF;
- materializar o acervo judicial inteiro como Markdown;
- criar uma segunda base de verdade;
- definir uma ontologia completa do Judiciário brasileiro;
- normalizar homônimos ou relações que as fontes não sustentam;
- exigir backend dinâmico ou SSR;
- colocar regras visuais do Cobogó no modelo de domínio;
- fazer o OKF depender da Web;
- obrigar MCP e Web a usarem a mesma serialização ou o mesmo runtime;
- remover proveniência em nome de uma visão “unificada”.

## 15. Alternativas rejeitadas

### 15.1. Tipos TypeScript como contrato canônico

Resolveriam a Web, mas deixariam Python/MCP e outros consumidores com semântica duplicada. Também fariam o contrato do produto pertencer à camada de apresentação.

### 15.2. Pydantic como contrato canônico

Melhoraria o MCP/backend, mas apenas inverteria o problema: o frontend continuaria precisando copiar o modelo e o conhecimento do produto ficaria preso a um runtime Python.

### 15.3. Parquet diretamente como contrato do produto

Schema físico não expressa bem relações, proveniência e significado público; além disso, otimizações de armazenamento passariam a ser breaking changes de produto.

### 15.4. Um JSON próprio intermediário

Criaria exatamente o dialeto ad hoc que esta RFC pretende evitar. JSON continua útil como transporte, mas não como fonte independente de semântica.

### 15.5. Persistir tudo em OKF

Duplicaria o acervo e introduziria sincronização, custo e uma nova fonte de verdade sem benefício proporcional. OKF governa conhecimento/contratos; Parquet governa o data plane.

## 16. Critérios de aceitação da RFC

A decisão é considerada implementada quando:

1. o bundle `knowledge/` contém os contratos mínimos do domínio público e passa na validação `okf-parser`;
2. existem regras relacionais para as invariantes adotadas, sem transformar convenções frágeis em constraints normativas;
3. existe um único adaptador semântico reutilizável entre consulta e superfícies de produto;
4. fixtures representativas cobrem pelo menos processo, publicação, proveniência, ausência parcial e conflito entre fontes;
5. uma projeção de processo é consumida tanto pela nova Web quanto pelo MCP sem redefinição independente de identidade/proveniência;
6. componentes Cobogó não conhecem Parquet, manifests ou rows DuckDB;
7. `publicacoes_buscar` e a Web de publicações compartilham a mesma semântica de domínio;
8. todo evento/publicação exibido consegue expor sua origem quando ela existe;
9. a nova Web mantém o modelo estático por padrão e não introduz servidor de runtime apenas para sustentar esta arquitetura;
10. RFC 0005, RFC 0009 e RFC 0014 permanecem válidas — esta RFC as conecta em uma fronteira semântica única.

## 17. Consequências

### Positivas

- uma linguagem de domínio única para humanos, agentes e UI;
- menor acoplamento entre armazenamento e produto;
- proveniência preservada desde a consulta até a tela;
- mudanças de schema físico deixam de vazar automaticamente para consumidores;
- Cobogó pode evoluir sem redefinir o domínio;
- MCP e Web deixam de competir como implementações independentes do produto;
- contratos de identidade e relação passam a ser testáveis de forma determinística.

### Custos

- passa a existir uma camada explícita de adaptação;
- o vocabulário semântico precisa de governança e versionamento;
- algumas estruturas hoje construídas diretamente em UI terão de ser movidas para o domínio;
- haverá custo inicial para criar fixtures e contratos relacionais.

Esses custos são deliberados: a alternativa já existe hoje, mas de forma implícita e duplicada em várias camadas.

## 18. Regra de evolução

Novos conceitos entram no contrato por necessidade observada de produto, não por antecipação taxonômica.

Uma nova fonte pode exigir um adaptador novo; não deve exigir que Cobogó ou cada tool aprendam seu schema. Uma nova interface pode exigir uma projeção nova; não deve redefinir `Processo`, `Publicacao` ou a proveniência.

A pergunta de revisão para qualquer extensão passa a ser:

> isto é uma nova evidência sobre conceitos que já temos, uma nova projeção para uma tarefa, ou realmente um novo conceito do domínio?

Só o terceiro caso amplia o vocabulário OKF.