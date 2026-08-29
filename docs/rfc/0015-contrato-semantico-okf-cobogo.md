# RFC 0015 — Contrato semântico do produto com OKF e apresentação Cobogó

- **Status:** Proposto
- **Data:** 2026-08-29
- **Depende de:** RFC 0005 (processo como recurso central), RFC 0009 (camada de dados da Web), RFC 0014 (MCP como superfície de produto)
- **Complementa:** o bundle `knowledge/` e seus contratos relacionais já validados por `okf-parser`
- **Escopo:** modelo semântico público do CausaGanha, fronteira entre preservação, dados e produto, conformidade externa e regras para a nova Web baseada em Cobogó

## 1. Resumo executivo

O CausaGanha já possui decisões arquiteturais corretas em planos diferentes:

1. o **processo judicial**, identificado pelo CNJ, é o recurso central do produto (RFC 0005);
2. os **artefatos preservados**, inclusive cópias dos dados das fontes oficiais publicadas no Internet Archive, conservam a evidência recebida em uma forma estável e auditável;
3. os **Parquets canônicos, manifests e índices finos** são o plano de dados em escala, consultado com DuckDB/DuckDB-WASM (RFC 0005 e RFC 0009);
4. o **MCP** expõe tarefas de produto, como consultar processo e buscar publicações, escondendo do agente detalhes de partições, joins e transporte (RFC 0014 e implementações posteriores).

Falta uma fronteira única que diga, independentemente da forma arquivada, do layout físico, do protocolo ou da interface visual, **o que é um processo, uma publicação, um evento, um documento, uma pessoa participante, um órgão judicial e a proveniência de cada afirmação**.

Esta RFC decide que:

- **OKF v0.2 é o formato canônico no qual o contrato semântico do produto é autorado, versionado e inspecionado**;
- **specs/TypeContracts do CausaGanha, mantidos dentro desse bundle, definem o schema de domínio que os runtimes devem obedecer**;
- **`okf-parser` é o compilador/validador relacional desse contrato**, inclusive para materializar uma representação DuckDB/Ibis consultável do conhecimento, tipos e relações;
- **os dados em massa continuam vindo das fontes que já existem**, preservados e transformados segundo as decisões vigentes; OKF não se torna origem nem espelho integral do acervo;
- **Parquet/DuckDB continuam sendo o plano canônico de dados e consulta em escala**;
- **Cobogó é a camada de apresentação da nova Web**;
- Web, MCP e futuras exportações devem derivar suas representações do mesmo modelo semântico, em vez de reconstruir conceitos diretamente a partir de rows, SQL ou componentes de UI;
- o modelo interno deve ser continuamente testado contra **perfis externos de interoperabilidade judicial**, de modo que sua capacidade de representar um processo não dependa apenas da nossa própria definição.

Em forma curta:

```text
fontes oficiais
      │
      ├──────────────→ preservação / Internet Archive
      │                 evidência no formato arquivado
      │
      ↓
Parquet + manifests + índices       plano de dados em escala
      │
      ↓
adaptação semântica conformante
      │
      ↓
modelo CausaGanha
  ↑
OKF + TypeContracts
  ↓
okf-parser → DuckDB/Ibis de referência
      │
      ├────────→ perfis CNJ/OASIS/LexML       prova de interoperabilidade
      │
      ↓
projeções orientadas à tarefa
      ↓
Web/Cobogó | MCP | exportações      superfícies de produto
```

**OKF é canônico para o significado e para o modelo autorado; Parquet é canônico para os registros em escala; os artefatos preservados são canônicos para aquilo que foi arquivado da fonte.** Essas afirmações governam planos diferentes e não criam fontes de verdade concorrentes.

## 2. Problema

A Web atual acumulou conhecimento de domínio em vários lugares ao mesmo tempo: SQL/query contracts, loaders, tipos TypeScript, componentes Svelte/Astro, textos explicativos e regras específicas de cada página. O MCP possui seus próprios modelos de retorno. Isso cria problemas previsíveis.

### 2.1. Semântica duplicada

Uma mesma ideia — por exemplo, “esta publicação pertence a este processo e veio do DJEN” — pode ser reconstruída de modos diferentes pela Web e pelo MCP. Se cada consumidor define seus próprios campos, nulabilidade, identidade e regras de reconciliação, a divergência é apenas uma questão de tempo.

### 2.2. Acoplamento entre produto e armazenamento

DuckDB, Parquet, nomes de arquivos e partições são mecanismos de consulta. Não devem definir a linguagem pública do produto. Uma página de processo não deveria precisar saber se um evento veio de uma row de `comunicacoes`, de um índice fino ou de uma view temporária para decidir o que significa “publicação”.

### 2.3. Proveniência tratada como detalhe de implementação

No CausaGanha, a origem de um dado é parte do próprio dado. DJEN, DataJud, TJRO JURIS e STJ podem registrar aspectos diferentes — ou aparentemente conflitantes — do mesmo processo. Uma camada de apresentação que recebe apenas valores já achatados perde a capacidade de dizer de onde cada afirmação veio.

### 2.4. Preservação, consulta e semântica podem ser confundidas

O CausaGanha também funciona como arquivo. A forma em que uma coleta é preservada e publicada no Internet Archive existe por razões de fidelidade, custo, desempenho, reprodutibilidade e distribuição. Essa forma **não precisa ser o melhor modelo para consultar o domínio** e não deve ser modificada apenas para servir à Web.

Do mesmo modo, uma representação relacional excelente para consulta não precisa substituir o artefato preservado. A arquitetura precisa permitir que o mesmo dado tenha uma forma arquivada, uma forma física otimizada para consulta e uma interpretação semântica comum, cada uma com responsabilidade própria.

### 2.5. Um contrato autorreferente é insuficiente

É possível construir um modelo internamente consistente e ainda assim modelar mal um processo judicial. Validar apenas nossos próprios schemas prova consistência, não aderência ao domínio.

O modelo deve, portanto, demonstrar que consegue projetar seu núcleo portável para modelos jurídicos externos reconhecidos sem inventar fatos e sem descartar silenciosamente informação essencial.

## 3. Decisão arquitetural

### 3.1. OKF governa o modelo autorado, não o acervo em massa

O repositório já usa `knowledge/` para fatos e contratos estáveis do projeto. O bundle atualmente modela fontes e pipelines e deixa explicitamente os datasets judiciais no plano Parquet/DuckDB. Esta RFC **estende esse desenho**, não o substitui.

O bundle passa a conter:

- conceitos e relações estáveis do domínio;
- specs/TypeContracts dos tipos públicos;
- regras de identidade, cardinalidade e proveniência;
- regras de mapeamento entre fontes e domínio;
- perfis de conformidade externos;
- fixtures pequenas, representativas e auditáveis.

OKF v0.2, por si só, não define uma taxonomia jurídica nem substitui schemas de domínio. A taxonomia e os campos do CausaGanha são extensões autoradas no bundle e compiladas/validadas pelo `okf-parser`.

Modelos Pydantic, tipos TypeScript e outras estruturas de runtime são **bindings ou projeções do contrato**, nunca definições independentes do que `Processo`, `Publicacao` ou `Documento` significam.

### 3.2. O DuckDB do `okf-parser` é representação relacional de referência

Uma vantagem deliberada do OKF é permitir modelar conhecimento e relações em Markdown legível e, em seguida, projetá-los para relações consultáveis.

O `okf-parser` pode materializar o bundle em DuckDB/Ibis e compilar os tipos declarados em relações tipadas. Essa representação é adotada como **plano relacional de referência do contrato**, útil para:

- consultar conceitos e relações enquanto o modelo está sendo desenhado;
- testar joins e cardinalidades antes de aplicá-los ao acervo massivo;
- inspecionar proveniência e conflitos em fixtures pequenas;
- escrever invariantes relacionais determinísticas;
- gerar relatórios de cobertura de mapeamento;
- fornecer aos agentes uma superfície de query simples sobre o modelo e a documentação semântica.

Isso **não** significa copiar milhões de processos para o DuckDB produzido a partir do bundle OKF. O DuckDB do bundle descreve e exercita o contrato; DuckDB sobre Parquet executa consultas sobre o acervo.

Os dois podem compartilhar a mesma álgebra relacional e, quando útil, as mesmas views/mapeamentos, mas têm escalas e responsabilidades diferentes.

### 3.3. OKF não vira banco de dados judicial

Esta RFC **não** manda converter milhões de publicações ou processos em milhões de arquivos Markdown.

Os registros em massa continuam em Parquet e são localizados pelos manifests, catálogo e índices existentes. Uma consulta pode produzir uma **projeção semântica transitória** de um processo ou conjunto de publicações conforme o contrato autorado no bundle, sem materializar essa projeção como novo corpus persistente.

Esta distinção é normativa: uma implementação que mantenha uma cópia OKF persistente de todo o acervo como nova fonte de verdade viola esta RFC.

### 3.4. Preservação no Internet Archive permanece independente

A publicação de snapshots no Internet Archive continua preservando a representação definida pelos pipelines de arquivo. A RFC não exige reempacotar esses snapshots em OKF, MNI, MTD ou qualquer outro modelo semântico.

A camada semântica deve conseguir apontar para o artefato preservado que sustenta uma afirmação e registrar a política usada para interpretá-lo. O artefato arquivado é evidência; o contrato OKF explica como o CausaGanha o entende.

### 3.5. Uma fronteira normativa, implementações conformantes

Existe uma única **fronteira e especificação normativa de adaptação** entre o plano físico e o modelo de domínio. Não é necessário que Web e MCP executem o mesmo binário.

Quando runtimes diferentes exigirem implementações distintas, elas devem:

- consumir o mesmo contrato autorado;
- usar a mesma definição de identidade e nulabilidade;
- passar pelo mesmo corpus de fixtures;
- produzir resultados semanticamente equivalentes;
- não introduzir reconciliação própria fora da fronteira.

Transformações expressáveis em SQL/DuckDB devem ser preferidas quando isso permitir compartilhar a mesma implementação entre DuckDB nativo e DuckDB-WASM sem deslocar o contrato semântico para o SQL.

```text
row física ──X──> componente Cobogó
row física ──X──> schema MCP independente

row física ──> mapping conformante ──> modelo semântico ──> Cobogó/MCP
```

## 4. Modelo semântico mínimo

A primeira versão deve ser pequena. A RFC deliberadamente não tenta criar uma ontologia completa do Judiciário brasileiro.

Os tipos iniciais são:

| Tipo | Identidade mínima | Papel no produto |
| --- | --- | --- |
| `Processo` | CNJ normalizado | recurso central e agregador verificável |
| `Publicacao` | identidade namespaced pela fonte | ato/publicação oficialmente encontrada no acervo |
| `EventoProcessual` | identidade namespaced pela fonte | acontecimento mostrado na linha do tempo |
| `Documento` | identidade da ocorrência na fonte | documento ou decisão associável ao processo |
| `Pessoa` | identificador disponível e escopo explícito | pessoa que aparece como participante |
| `InscricaoOAB` | número + UF, quando disponível | identificação profissional sem confundi-la com identidade civil |
| `OrgaoJudicial` | identificador/código da fonte com origem explícita | tribunal, órgão ou unidade responsável pelo registro |
| `Fonte` | nome estável já usado no bundle | sistema ou corpus que sustenta a evidência |

`Parte`, `advogado`, `autor`, `réu`, `recorrente` e papéis semelhantes são inicialmente **papéis de participação**, não novos tipos de pessoa. Uma `Pessoa` pode possuir zero ou mais `InscricaoOAB`; exercer o papel de advogado em um processo não torna a inscrição profissional sinônimo da pessoa.

Relações mínimas a representar e validar:

```text
Publicacao        → Processo
EventoProcessual  → Processo
EventoProcessual  → Publicacao | Documento
Documento         → Processo
Pessoa            → Processo        [papel sustentado pela fonte]
Pessoa            → InscricaoOAB
Pessoa            → Pessoa          [representação, quando sustentada]
OrgaoJudicial     → Publicacao | EventoProcessual | Processo
conceito          → Fonte           [proveniência]
```

Estruturas auxiliares de `EvidenciaFonte` e `CoberturaFonte` podem ser representadas como tipos ou value objects do contrato quando necessário. Elas devem permitir distinguir pelo menos:

- fonte consultada de fonte não coberta;
- registro ausente de coleta ausente;
- origem ao vivo de snapshot arquivado;
- instante/snapshot e escopo temporal relevante;
- evidência original de valor reconciliado ou derivado.

Os nomes físicos dos campos e relações são definidos nos specs/TypeContracts do bundle, não em componentes Cobogó nem em schemas MCP independentes.

## 5. Identidade

### 5.1. Processo

O identificador semântico de `Processo` é o CNJ normalizado de 20 dígitos, conforme a decisão já vigente na RFC 0005. A máscara é apresentação, nunca identidade.

### 5.2. Registros oriundos de fontes

Identificadores naturais de `Publicacao`, `EventoProcessual` e `Documento` são sempre namespaced pela fonte e pelo tipo. Um `id=123` no DJEN não é, por coincidência, o mesmo objeto que `id=123` em outra fonte.

Conceitualmente, uma identidade natural tem a forma:

```text
(fonte, tipo, source_id)
```

Quando a fonte não oferecer chave estável, o adaptador pode produzir chave determinística a partir de coordenadas imutáveis do registro. A política e sua versão fazem parte do contrato:

```text
(fonte, tipo, key_algorithm_version, deterministic_key)
```

Digest de conteúdo é propriedade de conteúdo e não deve ser confundido automaticamente com identidade da ocorrência. Duas fontes podem preservar o mesmo documento e continuar representando duas evidências distintas.

Uma posição de array, número de página da Web, ordem atual de query ou índice de lista **não** é identidade válida.

### 5.3. Pessoas

O modelo não deve alegar identidade civil que a fonte não prova. Nome igual não significa pessoa igual. Na ausência de identificador suficiente, a pessoa permanece escopada à ocorrência/fonte e não é reconciliada silenciosamente com homônimos.

## 6. Proveniência, reconciliação e conflito

OKF v0.2 torna `sources` e proveniência parte estrutural do formato. O CausaGanha deve aproveitar essa semântica em vez de inventar um segundo mecanismo de “fonte” apenas para a Web.

Regras normativas:

1. toda afirmação material exibida como fato derivado de fonte externa deve ser rastreável à sua fonte;
2. `resource`/localizadores devem apontar, quando possível, para o artefato oficial ou preservado que sustenta o conceito;
3. a origem **ao vivo** e a origem **arquivada** não podem ser tratadas como equivalentes silenciosamente;
4. reconciliação agrega evidências; não apaga valores divergentes de origem;
5. um valor derivado deve distinguir a regra de projeção da evidência que a alimentou;
6. a UI pode ocultar detalhes de proveniência por progressive disclosure, mas não pode descartá-los antes da camada de apresentação;
7. ausência de registro e ausência de cobertura são estados semanticamente diferentes;
8. validações de proveniência que o `okf-parser` ainda não ofereça nativamente devem ser expressas como contratos/regras relacionais do CausaGanha, e não presumidas como garantidas pelo parser.

Quando duas fontes discordarem, o contrato deve permitir transportar ambas as afirmações com suas origens. Escolher um “valor vencedor” só é permitido quando existir regra de reconciliação explícita e testável; mesmo assim, os valores de origem permanecem acessíveis.

## 7. Perfis externos de conformidade

O modelo interno não é definido por nenhum padrão externo específico. Padrões externos funcionam como **testes independentes de realidade semântica**.

A incapacidade de projetar um campo para determinado padrão não é automaticamente um erro: o CausaGanha possui extensões legítimas, especialmente em proveniência, preservação, cobertura e conflito. O erro é não conseguir representar o núcleo portável esperado, ou conseguir fazê-lo apenas inventando informação que a fonte não fornece.

### 7.1. CNJ DataJud — Modelo de Transmissão de Dados (MTD)

O MTD é o principal perfil estrutural brasileiro para o primeiro gate. O CNJ define o MTD para transmissão de dados processuais ao DataJud e publica seu XSD. O próprio CNJ registra que o MTD foi desenvolvido com base no MNI 2.2.2.

Referência oficial: <https://datajud-wiki.cnj.jus.br/mtd/>

O perfil `cnj-mtd` deve mapear, quando aplicável, pelo menos:

- número CNJ;
- tribunal/grau e órgão julgador;
- classe e assuntos;
- participantes e representação;
- movimentos/eventos;
- documentos e decisões quando representáveis;
- metadados temporais necessários ao modelo.

### 7.2. CNJ Modelo Nacional de Interoperabilidade (MNI) 2.2.2

O MNI é o perfil brasileiro de interoperabilidade operacional e fornece XSD/WSDL de intercomunicação.

Referência oficial: <https://www.cnj.jus.br/versao-2-2-2-07-07-2014/>

Como MTD deriva do MNI, os dois perfis não são tratados como validações estatisticamente independentes. Eles exercitam finalidades diferentes: MTD testa a representação transmissível ao DataJud; MNI testa a compatibilidade com a linguagem de interoperabilidade processual do CNJ.

### 7.3. OASIS LegalXML Electronic Court Filing 5.01

O OASIS ECF 5.01 é o perfil internacional independente. Ele define um modelo interoperável para processos, participantes, documentos, eventos/docketing e operações de filing.

Referência oficial: <https://www.oasis-open.org/standard/electronic-court-filing-version-5-01/>

O perfil usa a especificação XML normativa. A representação JSON do ECF 5.01, publicada pelo OASIS como representação alternativa, pode ser usada adicionalmente para testes de bindings e serialização, sem substituir o perfil normativo.

Referência JSON: <https://docs.oasis-open.org/legalxml-courtfiling/ecf-json/v5.0/ecf-json-v5.0.html>

### 7.4. LexML Brasil

LexML não é perfil de processo completo. Ele é usado onde sua competência é forte: `Documento`, especialmente normas, jurisprudência, publicações oficiais, identificação persistente por URN e vocabulários jurídicos.

Referência oficial: <https://projeto.lexml.gov.br/>

A incapacidade de converter `Processo` inteiro para LexML não é falha. A incapacidade de projetar corretamente um `Documento` que declare conformidade LexML é.

### 7.5. Perfis são mapeamentos versionados

Os perfis devem ser autorados ou referenciados pelo bundle, por exemplo:

```text
knowledge/.okf/specs/processo.md
knowledge/.okf/specs/publicacao.md
knowledge/.okf/specs/documento.md
knowledge/.okf/conformance/cnj-mtd.md
knowledge/.okf/conformance/cnj-mni.md
knowledge/.okf/conformance/oasis-ecf.md
knowledge/.okf/conformance/lexml.md
```

O layout exato pode mudar; o requisito é que o mapeamento seja versionado, inspecionável e testável.

Schemas externos usados em CI devem ser fixados por versão e digest. O CI não deve depender de um “latest” remoto mutável. Quando a licença permitir, uma cópia ou cache verificável pode ser mantido no repositório com origem e versão explícitas.

## 8. Gate de conformidade no CI

O CI deve tratar os perfis externos como conformance tests do modelo, não como exportadores decorativos.

### 8.1. Conversão e validação estrutural

Fixtures canônicas do modelo interno são convertidas para os perfis aplicáveis e validadas contra os schemas oficiais fixados.

Exemplos de gates:

```text
Processo fixture → CNJ MTD XML → XSD MTD válido
Processo fixture → MNI XML      → XSD MNI válido
Processo fixture → OASIS ECF    → schema ECF válido
Documento fixture → LexML       → schema/vocabulário aplicável válido
```

### 8.2. Equivalência semântica

XML formalmente válido não basta. O CI deve verificar invariantes semânticas depois da projeção, incluindo quando aplicável:

- mesmo CNJ;
- mesma classe/assunto quando mapeáveis;
- mesmo órgão;
- mesmos participantes e papéis representáveis;
- mesmos eventos/movimentos representáveis;
- mesmos documentos e relações;
- nenhuma informação obrigatória fabricada apenas para satisfazer o schema.

### 8.3. Round-trip quando honesto

Quando um perfil externo tiver informação suficiente para reconstruir o núcleo interno, o CI deve testar:

```text
fixture externa
    ↓
modelo CausaGanha
    ↓
mesmo perfil externo
    ↓
equivalência semântica
```

Round-trip não significa igualdade byte a byte. Ordem, serialização e normalizações podem mudar; identidade e significado do núcleo compartilhado não.

### 8.4. Cobertura de mapeamento

Cada execução deve produzir um relatório determinístico que classifique propriedades do modelo em pelo menos:

- `mapped`: representável no perfil;
- `extension`: extensão legítima do CausaGanha;
- `not_applicable`: conceito fora do escopo do perfil;
- `lossy`: representável apenas com perda conhecida;
- `unmapped`: esperado como portável, mas ainda sem mapeamento.

`unmapped` em propriedade marcada como portável é erro. `extension` não é erro, mas precisa ser explícito.

O objetivo não é atingir 100% de equivalência com um padrão. É impedir que o CausaGanha crie sem perceber uma ontologia incompatível com o domínio que pretende representar.

## 9. Projeções de produto

O contrato é mais rico que uma resposta de tela ou uma tool individual. Consumidores não precisam receber o grafo inteiro.

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
    → Publicacao[] + Processo? + Pessoa? + fontes + paginação

/p/{CNJ}
    → a mesma projeção semântica de processo, apresentada por Cobogó
```

A serialização concreta pode ser JSON para transporte. **JSON não é o contrato semântico**; é apenas uma serialização de uma projeção cujo significado vem do modelo autorado.

## 10. Web nova: Cobogó como apresentação

Cobogó é adotado como camada visual da nova Web. Ele deve receber modelos já semânticos e não incorporar conhecimento de armazenamento.

### 10.1. Regra de dependência

Componentes de apresentação podem conhecer `Processo`, `Publicacao`, `EventoProcessual` e demais projeções de produto. Não podem conhecer:

- nomes de arquivos Parquet;
- partições por ano/tribunal;
- SQL de reconciliação;
- rows DuckDB cruas;
- detalhes do manifest necessários apenas para localizar dados.

O padrão desejado é:

```text
consulta → adaptação semântica → ProcessoView → componente Cobogó
```

Não:

```text
consulta → row DuckDB → componente que interpreta a row
```

### 10.2. Hierarquia do produto

A nova Web deve começar pelas tarefas públicas, não pela operação do pipeline. A navegação primária é:

```text
Buscar | Publicações | Sobre os dados
```

A busca inicial pode detectar CNJ, OAB e texto e encaminhar à tarefa apropriada. A página de processo é o principal dossiê verificável. Cobertura, saúde dos pipelines, downloads, DuckDB, Internet Archive e detalhes de preservação continuam disponíveis, mas pertencem a **Sobre os dados** e à transparência, não ao caminho principal de consulta.

### 10.3. Proveniência próxima da evidência

O novo site não deve abrir com uma aula de arquitetura. A proveniência aparece junto do fato que sustenta — por exemplo, um selo ou detalhe de fonte em uma publicação ou evento — e pode expandir para metadados técnicos quando o usuário desejar auditar.

## 11. MCP e outras superfícies

A RFC 0014 estabeleceu o MCP como superfície de produto. Esta RFC endurece a fronteira: tools orientadas ao usuário devem consumir as mesmas projeções semânticas que a Web sempre que representarem a mesma tarefa.

Isso não exige respostas byte a byte idênticas. MCP pode usar uma forma compacta adequada a agentes e Web pode usar uma view adequada à leitura. O que não pode divergir é identidade, interpretação, proveniência ou regra de reconciliação.

Um agente que chama `publicacoes_buscar` não precisa saber arquivo, partição, join ou transporte. Um componente Cobogó também não.

## 12. Uso de `okf-parser`

A adoção não se limita a escrever Markdown com frontmatter. O parser faz parte do contrato de engenharia.

A implementação deve:

1. estender o bundle `knowledge/` com os tipos e specs/TypeContracts de domínio;
2. exigir spec para os tipos públicos quando a adoção estiver concluída;
3. estender contratos relacionais para identidade, cardinalidade e referências que sejam realmente invariantes;
4. validar o bundle em CI com versão exata de `okf-parser`;
5. materializar uma representação DuckDB/Ibis de referência para inspeção e queries do modelo;
6. manter fixtures pequenas e representativas de projeções oriundas de DJEN, DataJud, TJRO JURIS e STJ;
7. testar implementações de adaptação contra essas fixtures e contra casos de conflito/ausência parcial;
8. executar os perfis de conformidade externos da seção 7;
9. usar relatórios determinísticos do parser para falhar de forma legível quando o contrato for violado.

Se uma capacidade necessária existir apenas em versão posterior do `okf-parser`, a atualização da dependência deve ser explícita e testada; esta RFC não autoriza faixa de versão móvel.

## 13. O que permanece no plano de dados e de preservação

Esta RFC não altera as decisões de armazenamento da RFC 0005/0009 nem o papel arquivístico do CausaGanha.

Continuam pertencendo ao plano de preservação/dados:

- respostas e arquivos capturados das fontes oficiais;
- ZIPs e snapshots preservados;
- itens publicados no Internet Archive;
- Parquets canônicos;
- manifests e logs append-only;
- `indice_processual.parquet`;
- catálogo;
- DuckDB/DuckDB-WASM como motores de consulta do acervo;
- poda de partições e estratégias de join.

A camada semântica pode usar tudo isso. Cobogó e as tools de produto não devem depender desses detalhes diretamente.

Nada nesta RFC exige alterar uma representação já escolhida para preservação apenas porque outra forma é melhor para consulta semântica.

## 14. Migração

A migração será incremental e não exige reescrita dos pipelines de coleta ou arquivo.

### Fase 1 — contrato OKF e DuckDB de referência

Modelar `Processo`, `Publicacao`, `EventoProcessual`, `Documento`, `Pessoa`, `InscricaoOAB` e `OrgaoJudicial`; criar specs/TypeContracts; ampliar os contratos relacionais; criar fixtures cross-fonte; materializar e consultar o modelo pelo `okf-parser`/DuckDB.

**Gate:** um CNJ representativo, com dados de mais de uma fonte quando disponíveis, é reconstruído por relações tipadas e consultável sem que o consumidor conheça schemas físicos.

### Fase 2 — perfis externos de conformidade

Implementar primeiro `cnj-mtd`, depois `cnj-mni`, `oasis-ecf` e os perfis LexML aplicáveis a documentos.

**Gate:** a mesma fixture interna passa pelos schemas externos aplicáveis e pelo conjunto de assertions de equivalência semântica, com relatório de cobertura de mapeamento.

### Fase 3 — casca Cobogó e busca

Criar a nova homepage e navegação primária com Cobogó, mantendo o site estático e a busca como protagonista. A homepage não migra dashboards operacionais, calendário demonstrativo ou componentes antigos por inércia.

**Gate:** o usuário consegue iniciar busca por CNJ/texto sem exposição prévia a detalhes de armazenamento.

### Fase 4 — dossiê de processo

Reimplementar a página de processo consumindo a projeção `Processo`, com conteúdo primeiro e proveniência auditável por evento/publicação/documento.

**Gate:** nenhum componente do dossiê interpreta row DuckDB crua e a fixture usada pela Web também passa pelos perfis externos aplicáveis.

### Fase 5 — publicações

Reimplementar busca e resultados de publicações sobre a mesma semântica usada por `publicacoes_buscar` no MCP.

**Gate:** Web e MCP concordam sobre identidade, fonte e relação com processo para as mesmas fixtures.

### Fase 6 — transparência do arquivo

Reagrupar cobertura, estado de coleta, metodologia, downloads, catálogo, DuckDB e Internet Archive em **Sobre os dados**, preservando a capacidade de auditoria sem transformar infraestrutura em navegação principal.

## 15. Política para funcionalidades antigas

Uma funcionalidade existente não migra para a nova Web apenas porque já existe.

Para entrar na nova superfície ela deve responder a uma tarefa concreta do usuário e poder ser expressa sobre o contrato semântico ou ser claramente classificada como ferramenta de transparência/operação.

`advogados`, `comparador`, `explorador`, `stats`, calendários, heatmaps e atalhos globais podem continuar acessíveis durante a transição, mas não recebem automaticamente lugar na nova hierarquia. Git preserva o código anterior; a nova arquitetura não precisa preservar cada decisão visual dentro da interface.

## 16. Não objetivos

Esta RFC não pretende:

- substituir Parquet ou DuckDB por OKF;
- substituir a representação dos snapshots publicados no Internet Archive;
- materializar o acervo judicial inteiro como Markdown;
- criar uma segunda base de verdade;
- declarar MTD, MNI, ECF ou LexML como modelo interno do CausaGanha;
- atingir equivalência total com qualquer padrão externo;
- definir uma ontologia completa do Judiciário brasileiro;
- normalizar homônimos ou relações que as fontes não sustentam;
- exigir backend dinâmico ou SSR;
- colocar regras visuais do Cobogó no modelo de domínio;
- fazer o OKF depender da Web;
- obrigar MCP e Web a usarem a mesma serialização ou o mesmo runtime;
- remover proveniência em nome de uma visão “unificada”.

## 17. Alternativas rejeitadas

### 17.1. Tipos TypeScript como contrato canônico

Resolveriam a Web, mas deixariam Python/MCP e outros consumidores com semântica duplicada. Também fariam o contrato do produto pertencer à camada de apresentação.

### 17.2. Pydantic como contrato canônico

Melhoraria o MCP/backend, mas apenas inverteria o problema: o frontend continuaria precisando copiar o modelo e o conhecimento do produto ficaria preso a um runtime Python.

### 17.3. Parquet diretamente como contrato do produto

Schema físico não expressa sozinho relações, proveniência e significado público; além disso, otimizações de armazenamento passariam a ser breaking changes de produto.

### 17.4. Um JSON próprio intermediário

Criaria exatamente o dialeto ad hoc que esta RFC pretende evitar. JSON continua útil como transporte, mas não como fonte independente de semântica.

### 17.5. Persistir tudo em OKF

Duplicaria o acervo e introduziria sincronização, custo e uma nova fonte de verdade sem benefício proporcional. OKF governa o modelo e o conhecimento autorado; Parquet governa o data plane em escala.

### 17.6. Adotar MNI/MTD diretamente como modelo interno

Daria aderência ao ecossistema CNJ, mas acoplaria o produto a uma finalidade de interoperabilidade/transmissão específica e deixaria sem representação natural extensões próprias de proveniência, conflito, cobertura e preservação.

O CausaGanha deve provar que conversa com esses modelos, não se reduzir a eles.

## 18. Critérios de aceitação da RFC

A decisão é considerada implementada quando:

1. o bundle `knowledge/` contém specs/TypeContracts mínimos do domínio público e passa na validação `okf-parser`;
2. o modelo pode ser consultado em uma representação DuckDB/Ibis de referência gerada/compilada a partir do bundle;
3. existem regras relacionais para as invariantes adotadas, sem transformar convenções frágeis em constraints normativas;
4. existe uma única especificação normativa de adaptação, com todas as implementações de runtime passando pelo mesmo corpus de conformidade;
5. fixtures representativas cobrem processo, publicação, proveniência, ausência parcial e conflito entre fontes;
6. identificadores de registros externos são namespaced e chaves sintéticas têm algoritmo/versionamento explícitos;
7. pelo menos o perfil `cnj-mtd` valida estrutural e semanticamente uma fixture de processo; os demais perfis são adicionados conforme a Fase 2;
8. o CI publica relatório de cobertura de mapeamento e não aceita `unmapped` em propriedade marcada como portável;
9. uma projeção de processo é consumida tanto pela nova Web quanto pelo MCP sem redefinição independente de identidade/proveniência;
10. componentes Cobogó não conhecem Parquet, manifests ou rows DuckDB;
11. `publicacoes_buscar` e a Web de publicações compartilham a mesma semântica de domínio;
12. todo evento/publicação exibido consegue expor sua origem quando ela existe;
13. ausência de registro e ausência de cobertura permanecem distinguíveis até as superfícies de produto;
14. a nova Web mantém o modelo estático por padrão e não introduz servidor de runtime apenas para sustentar esta arquitetura;
15. a preservação no Internet Archive continua independente da representação semântica;
16. RFC 0005, RFC 0009 e RFC 0014 permanecem válidas — esta RFC as conecta em uma fronteira semântica única.

## 19. Consequências

### Positivas

- uma linguagem de domínio única para humanos, agentes e UI;
- modelagem inicial simples em Markdown, com relações imediatamente consultáveis por DuckDB/Ibis;
- possibilidade de testar joins, cardinalidades e conflitos antes de aplicá-los ao acervo massivo;
- menor acoplamento entre armazenamento e produto;
- preservação e consulta deixam de competir por uma única representação física;
- proveniência preservada desde o arquivo até a tela;
- mudanças de schema físico deixam de vazar automaticamente para consumidores;
- Cobogó pode evoluir sem redefinir o domínio;
- MCP e Web deixam de competir como implementações independentes do produto;
- contratos de identidade e relação passam a ser testáveis de forma determinística;
- padrões jurídicos externos funcionam como testes diferenciais contra deriva ontológica;
- extensões próprias do CausaGanha permanecem possíveis, mas precisam ser explícitas.

### Custos

- passa a existir uma camada explícita de adaptação;
- o vocabulário semântico precisa de governança e versionamento;
- os perfis externos exigem mappings e fixtures de conformidade mantidos;
- schemas externos precisam ser fixados e atualizados deliberadamente;
- algumas estruturas hoje construídas diretamente em UI terão de ser movidas para o domínio;
- haverá custo inicial para criar fixtures e contratos relacionais.

Esses custos são deliberados: a alternativa já existe hoje, mas de forma implícita e duplicada em várias camadas.

## 20. Regra de evolução

Novos conceitos entram no contrato por necessidade observada de produto, não por antecipação taxonômica.

Uma nova fonte pode exigir um adaptador novo; não deve exigir que Cobogó ou cada tool aprendam seu schema. Uma nova interface pode exigir uma projeção nova; não deve redefinir `Processo`, `Publicacao` ou a proveniência.

Um novo padrão externo pode adicionar um perfil de conformidade sem se tornar fonte normativa do nosso domínio.

A pergunta de revisão para qualquer extensão passa a ser:

> isto é uma nova evidência sobre conceitos que já temos, uma nova projeção para uma tarefa, uma extensão própria que precisa ser declarada, ou realmente um novo conceito do domínio?

Só o último caso amplia o vocabulário central. Uma extensão própria deve explicar por que não pertence ao núcleo portável e como se comporta nos perfis externos aplicáveis.
