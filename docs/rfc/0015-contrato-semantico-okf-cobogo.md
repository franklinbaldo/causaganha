# RFC 0015 — Contrato semântico do produto com OKF e apresentação Cobogó

- **Status:** Proposto
- **Data:** 2026-08-29
- **Depende de:** RFC 0005 (processo como recurso central), RFC 0009 (camada de dados da Web), RFC 0014 (MCP como superfície de produto)
- **Complementa:** o bundle `knowledge/` e seus contratos relacionais já validados por `okf-parser`
- **Escopo:** modelo semântico público do CausaGanha, fronteira entre preservação, dados e produto, conformidade externa e regras para a nova Web baseada em Cobogó

## 1. Resumo executivo

**O OKF não contém o acervo; contém o modelo que torna o acervo inteligível.**

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
- **JSON Schema, Zod e Pydantic gerados pelo `okf-parser` são bindings derivados do mesmo TypeContract**;
- **os tipos TypeScript de domínio são inferidos ou gerados a partir do Zod gerado**, nunca redescritos manualmente;
- um barrel TypeScript manual é permitido apenas como **camada fina de nomes/reexports e `z.infer`**, sem campos, nulabilidade, refinamentos ou composição semântica próprios;
- **projeções de produto compartilhadas entre Web, MCP, backend ou exportações também pertencem ao contrato autorado** e devem gerar bindings, em vez de serem compostas semanticamente à mão no consumidor;
- **os dados em massa continuam vindo das fontes que já existem**, preservados e transformados segundo as decisões vigentes; OKF não se torna origem nem espelho integral do acervo;
- **Parquet/DuckDB continuam sendo o plano canônico de dados e consulta em escala**;
- **Cobogó é a camada de apresentação da nova Web**;
- Web, MCP e futuras exportações derivam suas representações do mesmo modelo semântico, em vez de reconstruir conceitos diretamente a partir de rows, SQL ou componentes de UI;
- o modelo interno deve ser continuamente testado contra **perfis externos de interoperabilidade judicial**, sem permitir que esses padrões externos substituam ou estreitem o TypeContract interno.

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
  okf-parser
   ├────────→ DuckDB/Ibis              query relacional de referência
   ├────────→ JSON Schema              binding interoperável
   ├────────→ Zod → z.infer            binding frontend/TypeScript
   └────────→ Pydantic                 binding Python/backend/MCP
      │
      ├────────→ perfis CNJ/OASIS/LexML       prova de interoperabilidade
      │
      ↓
projeções declaradas de produto
      ↓
Web/Cobogó | MCP | exportações      superfícies de produto
```

**OKF é canônico para o significado e para o modelo autorado; Parquet é canônico para os registros em escala; os artefatos preservados são canônicos para aquilo que foi arquivado da fonte.** DuckDB/Ibis, JSON Schema, Zod, Pydantic e tipos TypeScript derivados são representações do contrato, não novas autoridades semânticas.

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

Do mesmo modo, uma representação relacional excelente para consulta não precisa substituir o artefato preservado. A arquitetura permite que o mesmo dado tenha uma forma arquivada, uma forma física otimizada para consulta e uma interpretação semântica comum, cada uma com responsabilidade própria.

### 2.5. Um contrato autorreferente é insuficiente

É possível construir um modelo internamente consistente e ainda assim modelar mal um processo judicial. Validar apenas nossos próprios schemas prova consistência, não aderência ao domínio.

O modelo deve, portanto, demonstrar que consegue projetar seu núcleo portável para modelos jurídicos externos reconhecidos sem inventar fatos e sem descartar silenciosamente informação essencial.

### 2.6. Bindings de runtime não podem ser cópias manuais do domínio

Declarar à mão uma segunda versão em TypeScript/Zod ou Pydantic reintroduz exatamente a divergência que esta RFC pretende remover. Nulabilidade, listas, tipos temporais e campos novos podem derivar silenciosamente.

O frontend precisa de um contrato executável para validar os dados que recebe, e Python/MCP precisa da mesma garantia. Esses contratos devem ser **gerados do mesmo TypeContract autorado no bundle**.

No TypeScript, `okf-parser` gera os schemas Zod; o projeto pode manter um barrel fino para expor tipos convenientes:

```ts
export { ProcessoSchema } from "./generated/domain-schemas";
export type Processo = z.infer<typeof ProcessoSchema>;
```

Esse barrel **não é um segundo schema**. Ele não pode declarar campos, opcionalidade, nulabilidade, enums, refinamentos de domínio ou composições semânticas próprias. Se isso for necessário, a mudança pertence ao TypeContract ou a uma projeção declarada no bundle.

No Python, modelos Pydantic que representem conceitos ou projeções cobertos pelo contrato também devem ser gerados a partir do TypeContract. Wrappers estritamente operacionais continuam permitidos, mas não podem redescrever o domínio.

### 2.7. Projeções também podem virar uma segunda ontologia

Gerar `ProcessoSchema` não resolve o problema se `ProcessoView`, `ProcessoConsultarResult` ou `PublicacoesBuscarResult` forem compostos manualmente em cada runtime.

Uma composição que atravessa uma fronteira de produto — Web, MCP, backend, exportação ou cache estável — possui semântica e, portanto, deve ser **declarada como projeção do contrato**. O bundle deve dizer quais conceitos entram, quais relações são incluídas, quais campos são opcionais e qual proveniência acompanha a projeção.

Tipos locais continuam livres para estado de componente, loading, seleção, paginação visual e outras preocupações puramente de apresentação.

## 3. Decisão arquitetural

### 3.1. OKF governa o modelo autorado, não o acervo em massa

O repositório já usa `knowledge/` para fatos e contratos estáveis do projeto. O bundle atualmente modela fontes e pipelines e deixa explicitamente os datasets judiciais no plano Parquet/DuckDB. Esta RFC **estende esse desenho**, não o substitui.

O bundle passa a conter:

- conceitos e relações estáveis do domínio;
- specs/TypeContracts dos tipos públicos;
- projeções compartilhadas de produto;
- regras de identidade, cardinalidade e proveniência;
- regras de mapeamento entre fontes e domínio;
- perfis de conformidade externos;
- fixtures pequenas, representativas e auditáveis.

OKF v0.2, por si só, não define uma taxonomia jurídica nem substitui schemas de domínio. A taxonomia e os campos do CausaGanha são extensões autoradas no bundle e compiladas/validadas pelo `okf-parser`.

Modelos Pydantic, schemas Zod, tipos TypeScript e outras estruturas de runtime são **bindings ou projeções do contrato**, nunca definições independentes do que `Processo`, `Publicacao` ou `Documento` significam.

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

### 3.3. JSON Schema, Zod, TypeScript e Pydantic são bindings gerados

O `okf-parser` compila o mesmo `TypeContract` para JSON Schema, código Zod e código Pydantic. Esses produtos são **artefatos derivados**, nunca contratos autorados em paralelo.

Para a Web, o Zod gerado é o binding preferencial porque combina validação em runtime e tipos TypeScript deriváveis com `z.infer`. O fluxo esperado é:

```text
knowledge/.okf/specs/*.md
        ↓
TypeContract
        ↓
okf-parser export Zod
        ↓
generated/domain-schemas.ts
        ↓
barrel fino: export + z.infer
        ↓
frontend / Cobogó
```

O gerador atual não precisa emitir as linhas `export type`. Um barrel manual é permitido exclusivamente para nomes, reexports e aliases por `z.infer`. Qualquer declaração estrutural no barrel é violação desta RFC.

Para Python/MCP/backend, o fluxo equivalente é:

```text
knowledge/.okf/specs/*.md
        ↓
TypeContract
        ↓
okf-parser export Pydantic
        ↓
generated/domain_models.py
        ↓
backend / MCP
```

Modelos Pydantic manuais são permitidos apenas para estruturas fora do contrato de domínio — por exemplo, configuração interna, envelopes de transporte puramente operacionais ou estado de infraestrutura. Um modelo que represente `Processo`, `Publicacao`, `EventoProcessual`, `Documento` ou uma projeção declarada deve ser gerado ou mecanicamente derivado do TypeContract.

Os arquivos gerados podem ser commitados ou produzidos no build conforme a estratégia do repositório, mas **não podem ser editados manualmente**. Se forem commitados, o CI regenera e exige diff vazio; se forem produzidos no build, o CI deve compilar/importar e testar o resultado.

JSON Schema cumpre papel complementar: interoperabilidade com tooling, documentação de bindings e conformance entre runtimes.

### 3.4. Projeções compartilhadas são contratos declarados

Uma projeção que atravessa fronteiras de produto é parte da API semântica e deve ser declarada no bundle, ainda que seja uma composição de tipos já existentes.

Exemplos iniciais:

```text
ProcessoConsultar
  = Processo
  + participantes
  + eventos
  + publicacoes
  + documentos
  + fontes/cobertura

PublicacoesBuscar
  = Publicacao[]
  + Processo?
  + Pessoa?
  + fontes
  + paginacao
```

O mecanismo de declaração é o **export referencial com projeções declaradas** do `okf-parser` (RFC 0018 daquele repositório, `rfcs/0018-referential-schema-export-and-projections.md`, aceita em 29/08/2026): a composição é lida do `okf.schema.sql` do bundle — que já declara as chaves estrangeiras entre tipos — e um documento `type: Projection` nomeia a raiz e as relações a percorrer. O binding gerado **referencia** `ProcessoSchema`, em vez de re-inlinar a estrutura de `Processo` dentro da projeção.

Essa distinção é normativa e não é detalhe de implementação. Uma projeção que inline a estrutura dos tipos referenciados produz uma segunda cópia do domínio que pode divergir do tipo-base sem que nenhum gate da seção 8.5 perceba, porque cada artefato permanece internamente consistente. Uma projeção que só é aceitável se referenciar não pode ser aproximada por inlining enquanto o mecanismo não existe.

Uma view puramente visual pode envolver uma projeção declarada, porém não pode acrescentar fatos ou relações de domínio. Se `ProcessoView` possui um campo que muda o significado do processo, esse campo pertence à projeção contratual; se possui apenas `expanded`, `selectedTab` ou `isLoading`, pertence à UI.

### 3.5. OKF não vira banco de dados judicial

Esta RFC **não** manda converter milhões de publicações ou processos em milhões de arquivos Markdown.

Os registros em massa continuam em Parquet e são localizados pelos manifests, catálogo e índices existentes. Uma consulta pode produzir uma **projeção semântica transitória** de um processo ou conjunto de publicações conforme o contrato autorado no bundle, sem materializar essa projeção como novo corpus persistente.

Esta distinção é normativa: uma implementação que mantenha uma cópia OKF persistente de todo o acervo como nova fonte de verdade viola esta RFC.

### 3.6. Preservação no Internet Archive permanece independente

A publicação de snapshots no Internet Archive continua preservando a representação definida pelos pipelines de arquivo. A RFC não exige reempacotar esses snapshots em OKF, MNI, MTD ou qualquer outro modelo semântico.

A camada semântica deve conseguir apontar para o artefato preservado que sustenta uma afirmação e registrar a política usada para interpretá-lo. O artefato arquivado é evidência; o contrato OKF explica como o CausaGanha o entende.

### 3.7. Uma fronteira normativa, implementações conformantes

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

row física ──> mapping conformante ──> modelo semântico ──> projeção declarada ──> Cobogó/MCP
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
knowledge/.okf/projections/processo-consultar.md
knowledge/.okf/projections/publicacoes-buscar.md
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
Processo fixture  → CNJ MTD XML → XSD MTD válido
Processo fixture  → MNI XML     → XSD MNI válido
Processo fixture  → OASIS ECF   → schema ECF válido
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
- `not_projectable`: a instância interna é válida, mas não possui informação exigida para uma projeção válida naquele perfil;
- `unmapped`: esperado como portável, mas ainda sem mapeamento.

`unmapped` em propriedade marcada como portável é erro. `extension`, `not_applicable` e `lossy` não são erros por si só, mas precisam ser explícitos. `not_projectable` é um resultado válido para uma instância específica quando a ausência decorre honestamente do contrato/fonte; nunca autoriza inventar dados.

O objetivo não é atingir 100% de equivalência com um padrão. É impedir que o CausaGanha crie sem perceber uma ontologia incompatível com o domínio que pretende representar.

### 8.5. Anti-drift dos bindings gerados

O CI deve verificar que todas as representações derivadas do TypeContract continuam sincronizadas:

```text
OKF/TypeContract
   ├─→ DuckDB/Ibis
   ├─→ JSON Schema
   ├─→ Zod → barrel fino → TypeScript
   └─→ Pydantic → Python/MCP
```

O gate mínimo é:

1. gerar os artefatos a partir do bundle com a versão fixada do `okf-parser`;
2. compilar o TypeScript/Zod produzido e importar o Pydantic produzido;
3. typecheckar os consumidores TypeScript a partir de `z.infer`/aliases finos;
4. validar a mesma fixture canônica com Zod e Pydantic;
5. validar projeções declaradas, e não apenas tipos atômicos;
6. se artefatos gerados estiverem versionados, exigir diff vazio após regeneração;
7. falhar se o barrel TypeScript contiver qualquer coisa além de reexports do arquivo gerado e aliases `z.infer` — verificação sintática determinística, e o barrel deixa de existir quando o gerador emitir os aliases;
8. falhar se uma projeção — declarada ou transitória — inlinar campos de um tipo referenciado em vez de referenciar seu schema gerado.

Cópias estruturais em modelos Pydantic manuais não são mecanicamente detectáveis e permanecem critério de revisão humana, não gate de CI. A RFC não finge que o CI as pega.

A mesma fixture que passa pela adaptação do data plane deve ser aceita pelos bindings gerados dos runtimes que a consomem. Web e MCP não podem divergir silenciosamente porque um deles copiou o schema.

### 8.6. Precedência entre contrato interno e perfis externos

O **TypeContract interno é normativo para o CausaGanha**. MTD, MNI, ECF e LexML são perfis de conformidade, não fontes de requiredness do nosso modelo.

Portanto:

1. um campo obrigatório no padrão externo **não torna automaticamente o campo obrigatório no TypeContract**;
2. um conversor nunca pode fabricar valor apenas para satisfazer XSD/schema externo;
3. cada perfil deve declarar suas precondições de projeção;
4. uma instância interna válida que não satisfaz essas precondições resulta em `not_projectable`/`lossy` conforme o caso, com explicação determinística;
5. o CI deve possuir pelo menos uma fixture que satisfaça honestamente as precondições de cada perfil obrigatório e valide contra o schema oficial;
6. uma divergência só deve provocar mudança no modelo interno quando revelar um defeito de domínio independente do padrão, e não porque o padrão escolheu uma cardinalidade ou obrigatoriedade diferente.

Assim, o gate externo é **evidência contra erro de modelagem**, não mecanismo para transformar o CausaGanha em uma cópia do MTD/MNI/ECF.

## 9. Projeções de produto

O contrato é mais rico que uma resposta de tela ou uma tool individual. Consumidores não precisam receber o grafo inteiro.

Cada tarefa pode definir uma **projeção orientada ao uso**, desde que preserve:

- identidades canônicas;
- significado dos campos;
- relações necessárias à tarefa;
- proveniência relevante;
- distinção entre ausência de registro e ausência de cobertura.

Projeções que atravessam fronteiras de produto devem ser declaradas no bundle e gerar bindings. Exemplos:

```text
processo_consultar(CNJ)
    → ProcessoConsultar
    → Processo + participantes + eventos + publicações + documentos + fontes

publicacoes_buscar(...)
    → PublicacoesBuscar
    → Publicacao[] + Processo? + Pessoa? + fontes + paginação

/p/{CNJ}
    → ProcessoConsultar apresentada por Cobogó
```

A Web e o MCP podem serializar ou apresentar a projeção de modos diferentes, mas não podem redefinir sua composição semântica.

A serialização concreta pode ser JSON para transporte. **JSON não é o contrato semântico**; é apenas uma serialização de uma projeção cujo significado vem do modelo autorado.

## 10. Web nova: Cobogó como apresentação

Cobogó é adotado como camada visual da nova Web. Ele deve receber modelos já semânticos e não incorporar conhecimento de armazenamento.

### 10.1. Regra de dependência

Componentes de apresentação podem conhecer conceitos e projeções de produto por meio dos bindings gerados. Não podem conhecer:

- nomes de arquivos Parquet;
- partições por ano/tribunal;
- SQL de reconciliação;
- rows DuckDB cruas;
- detalhes do manifest necessários apenas para localizar dados.

O padrão desejado é:

```text
consulta → adaptação semântica → projeção declarada → Zod gerado → tipo inferido → componente Cobogó
```

Não:

```text
consulta → row DuckDB → interface TypeScript manual → ProcessoView semântica local → componente
```

Schemas Zod do domínio e das projeções validam a fronteira de dados; componentes podem definir tipos próprios exclusivamente para estado visual, composição e apresentação.

### 10.2. Hierarquia do produto

A nova Web deve começar pelas tarefas públicas, não pela operação do pipeline. A navegação primária é:

```text
Buscar | Publicações | Sobre os dados
```

A busca inicial pode detectar CNJ, OAB e texto e encaminhar à tarefa apropriada. A página de processo é o principal dossiê verificável. Cobertura, saúde dos pipelines, downloads, DuckDB, Internet Archive e detalhes de preservação continuam disponíveis, mas pertencem a **Sobre os dados** e à transparência, não ao caminho principal de consulta.

### 10.3. Proveniência próxima da evidência

O novo site não deve abrir com uma aula de arquitetura. A proveniência aparece junto do fato que sustenta — por exemplo, um selo ou detalhe de fonte em uma publicação ou evento — e pode expandir para metadados técnicos quando o usuário desejar auditar.

## 11. MCP e outras superfícies

A RFC 0014 estabeleceu o MCP como superfície de produto. Esta RFC endurece a fronteira: tools orientadas ao usuário devem consumir as mesmas projeções semânticas declaradas que a Web quando representarem a mesma tarefa.

Isso não exige respostas byte a byte idênticas. MCP pode usar uma serialização compacta adequada a agentes e Web pode usar composição visual adequada à leitura. O que não pode divergir é identidade, interpretação, composição da projeção, proveniência ou regra de reconciliação.

O binding Python preferencial para conceitos/projeções cobertos pelo contrato é o Pydantic gerado pelo `okf-parser`. O MCP não deve manter modelos Pydantic manuais semanticamente equivalentes.

## 12. Uso de `okf-parser`

A adoção não se limita a escrever Markdown com frontmatter. O parser faz parte do contrato de engenharia.

A implementação deve:

1. estender o bundle `knowledge/` com os tipos e specs/TypeContracts de domínio;
2. exigir spec para os tipos públicos quando a adoção estiver concluída;
3. declarar no bundle as projeções compartilhadas entre superfícies;
4. estender contratos relacionais para identidade, cardinalidade e referências que sejam realmente invariantes;
5. validar o bundle em CI com versão exata de `okf-parser`;
6. materializar uma representação DuckDB/Ibis de referência para inspeção e queries do modelo;
7. exportar JSON Schema, Zod e Pydantic a partir dos mesmos TypeContracts;
8. usar o Zod gerado como binding de domínio/projeções do frontend e derivar dele tipos TypeScript por `z.infer` ou geração equivalente;
9. limitar barrels TypeScript manuais a nomes, reexports e aliases sem estrutura semântica;
10. usar Pydantic gerado como binding Python para domínio/projeções consumidos por backend e MCP;
11. impedir drift de artefatos gerados por regeneração determinística no CI;
12. manter fixtures pequenas e representativas de projeções oriundas de DJEN, DataJud, TJRO JURIS e STJ;
13. testar implementações de adaptação contra essas fixtures e contra casos de conflito/ausência parcial;
14. executar os perfis de conformidade externos da seção 7 respeitando a precedência da seção 8.6;
15. usar relatórios determinísticos do parser para falhar de forma legível quando o contrato for violado.

Se uma capacidade necessária existir apenas em versão posterior do `okf-parser`, a atualização da dependência deve ser explícita e testada; esta RFC não autoriza faixa de versão móvel.

A versão pinada hoje (`okf-parser 0.43`) **não** possui o mecanismo exigido pela seção 3.4: `build_schema_contracts` compila um contrato fechado por tipo, sem nó de referência entre tipos, e a camada de export não lê o `okf.schema.sql`.

O mecanismo existe no `main` do `okf-parser` desde 30/08/2026 — export referencial (`--relational-schema`, `--refs=key|embed`), documentos `type: Projection` e export das projeções pelos três formatos —, mas **ainda não em versão publicada**: o `pyproject.toml` daquele repositório declara `0.45.4` e a última release pública é `v0.45.2`. A condição da Fase 1b, portanto, deixou de ser "o parser precisa ganhar o mecanismo" e passou a ser "o mecanismo precisa estar numa versão consumível": publicação da versão e atualização explícita e testada do pin. Esta RFC não autoriza consumir código não publicado, nem faixa de versão móvel. A Fase 1a não depende de nada disso e pode começar imediatamente.

Enquanto o pin não alcançar o mecanismo, é permitido compor a projeção no consumidor **desde que a composição referencie os schemas gerados** (`z.object({ processo: ProcessoSchema, ... })`), nunca redeclarando os campos dos tipos referenciados. Essa composição é transitória, deve viver em um único arquivo por runtime e é substituída pela projeção declarada assim que o parser a suportar. Inlinar estrutura de tipo referenciado, em qualquer runtime, é violação desta RFC mesmo em regime transitório.

Pelo mesmo motivo, o barrel fino da seção 3.3 é transitório: quando o renderer Zod emitir os aliases `export type X = z.infer<typeof XSchema>`, o arquivo gerado passa a ser a superfície pública completa e o barrel deve ser removido em vez de fiscalizado.

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

### Fase 1a — contrato e plano relacional de referência

Modelar `Processo`, `Publicacao`, `EventoProcessual`, `Documento`, `Pessoa`, `InscricaoOAB` e `OrgaoJudicial`; criar specs/TypeContracts; ampliar contratos relacionais; criar fixtures cross-fonte; materializar e consultar o modelo pelo `okf-parser`/DuckDB.

**Gate:** um CNJ representativo, com dados de mais de uma fonte quando disponíveis, é reconstruído por relações tipadas e consultável no DuckDB/Ibis de referência sem que o consumidor conheça schemas físicos. Identidade, cardinalidade, proveniência mínima e conflitos das fixtures passam nas invariantes do contrato.

### Fase 1b — bindings e primeira projeção compartilhada

Gerar JSON Schema, Zod e Pydantic; declarar pelo menos `ProcessoConsultar`; validar a mesma fixture nos bindings de frontend e Python e consumir essa projeção em um caminho mínimo da Web/backend. **Depende** de uma versão publicada do `okf-parser` que carregue o export referencial e as projeções declaradas, e da atualização explícita e testada do pin; até lá vale a composição referencial transitória da seção 12.

**Gate:** a fixture `ProcessoConsultar` é aceita pelo Zod e pelo Pydantic gerados, TypeScript passa no typecheck usando apenas tipos derivados, Python importa/valida o modelo gerado, e não existe interface/model Pydantic manual semanticamente paralelo.

### Fase 2 — perfis externos de conformidade

Implementar primeiro `cnj-mtd`, depois `cnj-mni`, `oasis-ecf` e os perfis LexML aplicáveis a documentos.

**Gate:** pelo menos uma fixture que satisfaça honestamente as precondições de cada perfil obrigatório passa pelo schema externo e pelas assertions de equivalência semântica; instâncias internas válidas porém não projetáveis são relatadas explicitamente, sem fabricação de dados.

### Fase 3 — casca Cobogó e busca

Criar a nova homepage e navegação primária com Cobogó, mantendo o site estático e a busca como protagonista. A homepage não migra dashboards operacionais, calendário demonstrativo ou componentes antigos por inércia.

**Gate:** o usuário consegue iniciar busca por CNJ/texto sem exposição prévia a detalhes de armazenamento e os dados consumidos pela casca passam por projeção/binding gerados.

### Fase 4 — dossiê de processo

Reimplementar a página de processo consumindo `ProcessoConsultar`, com conteúdo primeiro e proveniência auditável por evento/publicação/documento.

**Gate:** nenhum componente do dossiê interpreta row DuckDB crua ou recompõe a semântica de `ProcessoConsultar`; a fixture usada pela Web também passa pelos perfis externos aplicáveis.

### Fase 5 — publicações

Declarar/estabilizar `PublicacoesBuscar` e reimplementar busca/resultados sobre a mesma projeção usada por `publicacoes_buscar` no MCP.

**Gate:** Web e MCP validam a mesma fixture de projeção e concordam sobre identidade, fonte e relação com processo.

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
- importar requiredness/cardinalidade de um perfil externo só para fazê-lo caber no modelo interno;
- exigir que toda instância interna seja exportável para todo perfil externo;
- atingir equivalência total com qualquer padrão externo;
- definir uma ontologia completa do Judiciário brasileiro;
- normalizar homônimos ou relações que as fontes não sustentam;
- exigir backend dinâmico ou SSR;
- colocar regras visuais do Cobogó no modelo de domínio;
- fazer o OKF depender da Web;
- obrigar MCP e Web a usarem a mesma serialização ou o mesmo runtime;
- tornar Zod, TypeScript ou Pydantic uma segunda fonte de verdade;
- remover proveniência em nome de uma visão “unificada”.

## 17. Alternativas rejeitadas

### 17.1. Tipos TypeScript ou Zod autorados como contrato canônico

Resolveriam a Web, mas deixariam Python/MCP e outros consumidores com semântica duplicada. Zod é valioso como binding executável **gerado**, e TypeScript como tipo derivado, não como lugar onde o significado do domínio nasce.

### 17.2. Pydantic como contrato canônico ou manual paralelo

Pydantic é um excelente binding Python, mas não deve ser a fonte do domínio nem uma cópia mantida à mão. Se for manual, o frontend volta a copiar o modelo; se for gerado do TypeContract, Web e backend permanecem ligados ao mesmo contrato.

### 17.3. Parquet diretamente como contrato do produto

Schema físico não expressa sozinho relações, proveniência e significado público; além disso, otimizações de armazenamento passariam a ser breaking changes de produto.

### 17.4. Um JSON próprio intermediário

Criaria exatamente o dialeto ad hoc que esta RFC pretende evitar. JSON continua útil como transporte, mas não como fonte independente de semântica.

### 17.5. Persistir tudo em OKF

Duplicaria o acervo e introduziria sincronização, custo e uma nova fonte de verdade sem benefício proporcional. OKF governa o modelo e o conhecimento autorado; Parquet governa o data plane em escala.

### 17.6. Adotar MNI/MTD diretamente como modelo interno

Daria aderência ao ecossistema CNJ, mas acoplaria o produto a uma finalidade de interoperabilidade/transmissão específica e deixaria sem representação natural extensões próprias de proveniência, conflito, cobertura e preservação.

O CausaGanha deve provar que conversa com esses modelos, não se reduzir a eles.

### 17.7. Compor projeções manualmente em cada runtime

Parece simples enquanto `ProcessoView` é pequeno, mas move relações, opcionalidade e escolhas de proveniência para Web/Python separadamente. A projeção compartilhada é parte do contrato e deve ser declarada uma vez.

## 18. Critérios de aceitação da RFC

A decisão é considerada implementada quando:

1. o bundle `knowledge/` contém specs/TypeContracts mínimos do domínio público e passa na validação `okf-parser`;
2. o modelo pode ser consultado em uma representação DuckDB/Ibis de referência gerada/compilada a partir do bundle;
3. JSON Schema, Zod e Pydantic são gerados dos mesmos TypeContracts e seus outputs passam por gate anti-drift;
4. os tipos TypeScript de domínio/projeção são inferidos/gerados do Zod e passam no typecheck dos consumidores;
5. qualquer barrel TypeScript manual é estruturalmente fino: nomes, reexports e `z.infer`, sem schema de domínio próprio;
6. modelos Pydantic de domínio/projeção usados por Python/MCP são gerados ou mecanicamente derivados do TypeContract, sem cópia estrutural manual concorrente;
7. projeções compartilhadas, começando por `ProcessoConsultar`, são declaradas no bundle e geram bindings nos runtimes que as consomem;
8. as mesmas fixtures de domínio/projeção são aceitas por Zod e Pydantic antes do consumo pelas superfícies;
9. existem regras relacionais para as invariantes adotadas, sem transformar convenções frágeis em constraints normativas;
10. existe uma única especificação normativa de adaptação, com todas as implementações de runtime passando pelo mesmo corpus de conformidade;
11. fixtures representativas cobrem processo, publicação, proveniência, ausência parcial e conflito entre fontes;
12. identificadores de registros externos são namespaced e chaves sintéticas têm algoritmo/versionamento explícitos;
13. pelo menos o perfil `cnj-mtd` valida estrutural e semanticamente uma fixture de processo que satisfaz suas precondições; os demais perfis são adicionados conforme a Fase 2;
14. o CI publica relatório de cobertura de mapeamento e não aceita `unmapped` em propriedade marcada como portável;
15. requiredness/cardinalidade de perfil externo não altera automaticamente o TypeContract; instâncias não projetáveis são relatadas sem fabricação de valores;
16. uma projeção de processo é consumida tanto pela nova Web quanto pelo MCP sem redefinição independente de identidade, composição ou proveniência;
17. componentes Cobogó não conhecem Parquet, manifests ou rows DuckDB;
18. `publicacoes_buscar` e a Web de publicações compartilham a mesma projeção semântica declarada;
19. todo evento/publicação exibido consegue expor sua origem quando ela existe;
20. ausência de registro e ausência de cobertura permanecem distinguíveis até as superfícies de produto;
21. a nova Web mantém o modelo estático por padrão e não introduz servidor de runtime apenas para sustentar esta arquitetura;
22. a preservação no Internet Archive continua independente da representação semântica;
23. RFC 0005, RFC 0009 e RFC 0014 permanecem válidas — esta RFC as conecta em uma fronteira semântica única.

## 19. Consequências

### Positivas

- uma linguagem de domínio única para humanos, agentes e UI;
- modelagem inicial simples em Markdown, com relações imediatamente consultáveis por DuckDB/Ibis;
- schemas JSON Schema, Zod e Pydantic derivados automaticamente do mesmo contrato;
- frontend com validação runtime e tipos TypeScript derivados sem duplicar manualmente o domínio;
- backend/MCP com modelos Pydantic derivados sem schema Python concorrente;
- projeções compartilhadas deixam de ser ontologias escondidas nos consumidores;
- possibilidade de testar joins, cardinalidades e conflitos antes de aplicá-los ao acervo massivo;
- menor acoplamento entre armazenamento e produto;
- preservação e consulta deixam de competir por uma única representação física;
- proveniência preservada desde o arquivo até a tela;
- mudanças de schema físico deixam de vazar automaticamente para consumidores;
- Cobogó pode evoluir sem redefinir o domínio;
- MCP e Web deixam de competir como implementações independentes do produto;
- contratos de identidade e relação passam a ser testáveis de forma determinística;
- padrões jurídicos externos funcionam como testes diferenciais contra deriva ontológica sem governar o modelo interno;
- extensões próprias do CausaGanha permanecem possíveis, mas precisam ser explícitas.

### Custos

- passa a existir uma camada explícita de adaptação;
- o vocabulário semântico e as projeções precisam de governança e versionamento;
- artefatos gerados precisam de política clara de build ou versionamento;
- barrels/wrappers precisam permanecer deliberadamente finos;
- os perfis externos exigem mappings e fixtures de conformidade mantidos;
- schemas externos precisam ser fixados e atualizados deliberadamente;
- algumas estruturas hoje construídas diretamente em UI ou MCP terão de ser movidas para o contrato;
- haverá custo inicial para criar fixtures e contratos relacionais.

Esses custos são deliberados: a alternativa já existe hoje, mas de forma implícita e duplicada em várias camadas.

## 20. Regra de evolução

Novos conceitos entram no contrato por necessidade observada de produto, não por antecipação taxonômica.

Uma nova fonte pode exigir um adaptador novo; não deve exigir que Cobogó ou cada tool aprendam seu schema. Uma nova interface pode exigir uma projeção nova; não deve redefinir `Processo`, `Publicacao` ou a proveniência.

Um novo padrão externo pode adicionar um perfil de conformidade sem se tornar fonte normativa do nosso domínio.

Uma mudança de TypeContract deve ser tratada como mudança do contrato de produto: regenerar DuckDB/Ibis, JSON Schema, Zod, Pydantic e os tipos TypeScript derivados é parte da mesma revisão. Um diff no binding gerado é evidência da mudança, não lugar para corrigi-la manualmente.

Uma mudança em uma projeção compartilhada também é mudança de contrato e precisa regenerar seus bindings e passar pelo corpus comum de fixtures.

A pergunta de revisão para qualquer extensão passa a ser:

> isto é uma nova evidência sobre conceitos que já temos, uma nova projeção para uma tarefa, uma extensão própria que precisa ser declarada, ou realmente um novo conceito do domínio?

Só o último caso amplia o vocabulário central. Uma extensão própria deve explicar por que não pertence ao núcleo portável e como se comporta nos perfis externos aplicáveis.
