# RFC 0014 — MCP como superfície de produto

- **Status:** M1 implementado; M2 implementado (com redesenho de dados —
  ver §2 M2 e a Emenda em RFC 0005)
- **Data:** 2026-07-22
- **Depende de:** RFC 0013 (Fase 3A/3B — fundação `causaganha_mcp`: cinco tools
  read-only, `register(mcp)` explícito, tradução de exceções na fronteira),
  RFC 0005 (processo como recurso unificado — base de dados para
  `processo_consultar`)
- **Escopo:** Descoberta/onboarding do servidor MCP, textos em português nas
  superfícies exibidas ao host, uma tool agregadora de status com
  freshness/proveniência estruturadas, e `processo_consultar` como a primeira
  tool MCP voltada ao usuário final (não ao operador).

## 1. Problema

RFC 0013 construiu a fundação do servidor `causaganha_mcp`: cinco tools
read-only (`datajud_status`, `tjro_juris_status`, `stj_acordaos_status`,
`djen_backup_status`, `datajud_facetas`), registro explícito, tradução de
erro na fronteira MCP. Isso resolveu "o servidor existe e funciona
corretamente". Não resolveu "alguém descobre que o servidor existe" nem "o
servidor entrega o que define o produto".

Quatro lacunas concretas:

- **Descoberta.** O README não lista `causaganha-mcp` entre os entrypoints —
  só CLI/Python e web. Instalar o projeto inteiro hoje não revela que o
  servidor existe, muito menos como configurá-lo num host MCP.
- **Idioma.** Titles, descriptions e nomes de campo das tools estão em
  inglês, mesmo sendo texto que o host MCP pode exibir diretamente ao
  usuário final — que, para este produto, é brasileiro.
- **Fragmentação operacional.** As quatro tools de status têm formatos
  heterogêneos (`count` no STJ vs. `total` nos demais), semânticas
  implícitas (o que "zero" significa varia por pipeline) e uma ressalva
  importante — o DJEN lê `sync-manifest.csv` local, não o parquet canônico
  no Internet Archive, podendo estar atrasado — enterrada na docstring, não
  no retorno. Um agente precisa chamar as quatro, e já saber essas
  diferenças de antemão, para montar um panorama.
- **Ausência do produto principal.** O causaganha já tem um dossiê
  reconciliado por CNJ (RFC 0005, com normalização de CNJ, paginação e
  apresentação já implementadas no dashboard web). O servidor MCP não expõe
  nada disso — só panoramas agregados de pipeline, que servem ao operador,
  não a quem quer saber o que está acontecendo num processo específico.

## 2. Proposta

Dois milestones sequenciais, cada um um PR.

### M1 — Experiência operacional (onboarding, PT-BR, status agregado)

**Onboarding.** Seção no README ("Use o CausaGanha no seu assistente") com:
configuração copiável do transporte stdio; distinção explícita entre as
tools locais (determinísticas, sem rede) e `datajud_facetas` (rede real);
cinco perguntas de exemplo cobrindo os casos de uso reais — "Como estão os
pipelines?", "Há uploads pendentes?", "Quais são as principais classes do
TJRO?", "Quais assuntos aparecem mais?", "Os dados locais podem estar
desatualizados?".

**Português nas superfícies exibidas.** `title`, `description` de cada tool
e os nomes/descrições de campo em `parameters`/`output_schema` passam para
português — são texto de produto, não identificador de código. Nomes de
função Python continuam em inglês (convenção do resto do repo); só o que o
protocolo MCP expõe ao host muda.

**Uniformização de schema (mudança deliberada, com teste de schema
exato).** Em vez de reconciliar nomes ad hoc, todas as tools locais passam a
retornar o mesmo envelope de campos:

```
encontrado        bool    — False quando não há manifest/dados nesta máquina
total / contagens  int     — específico de cada pipeline, mas sempre presente
ultima_atualizacao str|null — ver regra de proveniência abaixo
fonte              str     — "manifest_local" | "cache_local"
canonica           bool    — False quando a fonte não é a canônica (IA)
aviso              str|null — texto livre, só quando há ressalva real
```

Corrige também uma inconsistência hoje existente: `datajud_status` já
distingue manifest ausente com `encontrado=False`; `tjro_juris_status` e
`stj_acordaos_status` transformam arquivo ausente em contagens zeradas — um
agente não consegue hoje distinguir "pipeline genuinamente vazio" de
"nenhum dado nesta máquina". Ambos os casos passam a usar `encontrado=False`.

`datajud_facetas` (não é um pipeline local, mas ganha os campos que fazem
sentido para uma consulta ao vivo): `consultado_em` (timestamp da própria
consulta, não de um manifest), `tribunal` normalizado em minúsculas no
retorno.

**`causaganha_status` — tool agregadora.** Uma única tool que retorna todos
os pipelines locais num envelope comum:

```json
{
  "pipelines": [
    {
      "nome": "djen",
      "encontrado": true,
      "total": 12000,
      "concluido": 11500,
      "pendente": 300,
      "ultima_atualizacao": "2026-07-21T10:00:00-04:00",
      "fonte": "cache_local",
      "canonica": false,
      "aviso": "Pode estar atrás do manifest canônico no Internet Archive."
    }
  ]
}
```

Nome deliberadamente `status`/`overview`, não `health`: `saudável`/
`degradado` exigiria regras de negócio e limiares de freshness que ainda não
existem — inventá-los agora seria arquitetura por atalho.

### M2 — `processo_consultar` (fatia de produto para o usuário final)

Primeira tool MCP que serve diretamente quem quer saber sobre um processo
específico, não o operador do pipeline:

```
processo_consultar(cnj, incluir_documentos=true, limite_documentos=10)
```

Retorno: CNJ normalizado (e mascarado, `cnj_formatado`); `fontes_presentes`
(quais fontes têm registro para este CNJ) separado de `cobertura_dataset`
(estado de cada fonte na geração do dataset inteiro — distingue "fonte sem
este CNJ" de "fonte indisponível quando o dataset foi gerado"); resumo DJEN;
decisão/JURIS; STJ quando houver; capa oficial DataJud (RFC 0010); timestamp
de geração do dataset (`dataset_gerado_em`); documentos mais recentes;
`web_url` montado só quando a variável de ambiente `CAUSAGANHA_WEB_BASE_URL`
está configurada (nunca hardcoded — a tool não deve assumir onde o dashboard
está publicado).

**Investigação (concluída) → redesenho de dados, não só uma tool nova.** A
investigação de fonte de dados (parquets canônicos do IA vs. cache local)
levou a uma pergunta mais fundamental: a RFC 0005 original propunha uma
tabela larga `processos_unificados.parquet` como artefato canônico
publicado, mas o DJEN já resolvia o mesmo problema — "que registros existem
para este CNJ e onde estão" — de outra forma: um índice fino (`processos` em
`causaganha/consolidate/schema_registry.py`) que só aponta para o registro
completo, nunca copia seus campos. Generalizar esse padrão para as quatro
fontes (`indice_processual.parquet`) em vez de repetir o desenho da tabela
larga evita uma segunda fonte de verdade que pode divergir do conteúdo de
origem. Ver a Emenda no topo de RFC 0005 para o schema completo e o
raciocínio.

Como o índice já existe e é publicado (o reconciliador precisava ser
reescrito de qualquer forma), este M2 entrega o redesenho completo na mesma
PR, não só a tool: `scripts/reconcile_processos.py` publica
`indice_processual.parquet` (+ `indice_processual.report.json` de
cobertura) em vez das duas tabelas largas; `scripts/render_queries.py`
recomputa `processos_unificados`/`processo_documentos` como *views* DuckDB
em memória a partir das fontes de origem (só para os `.qmd` que ainda
precisam da forma larga, como `processos_multi_fonte.qmd` — nunca mais como
arquivo publicado); `causaganha.processos.service.buscar_processo` e
`web/src/lib/processoCnj.ts` (dashboard `/processo`) consultam o índice
primeiro para descobrir quais parquets de origem têm registro, depois
consultam esses parquets diretamente — a mesma consulta em duas linguagens
(DuckDB Python / DuckDB-WASM no navegador), mesmo padrão de dois estágios;
`datajud.service`'s descoberta de CNJs lê `indice_processual.parquet` (um
`SELECT DISTINCT numero_processo`, sem join) em vez do antigo
`processos_unificados.parquet`.

## 3. Regras específicas (para não abrir atalhos)

- **`causaganha_status` reutiliza as funções/modelos de `service.py` de cada
  pacote diretamente** (mesma chamada que `datajud_status` etc. já fazem) —
  nunca chama as quatro tools através do próprio protocolo MCP. Ir por dentro
  do protocolo para montar uma resposta que o próprio protocolo vai servir de
  novo é indireção sem propósito, e acopla a tool agregadora ao registro de
  tools do servidor em vez de à camada de serviço.
- **Sem `saudável`/`degradado`.** Toda tool de status (individual ou
  agregada) retorna fatos — `encontrado`, contagens, `ultima_atualizacao`,
  `fonte`, `canonica`, `aviso` — nunca um veredito. Inferir "saúde" exige
  limiares de freshness e regras de negócio que este RFC não define.
- **Manifest ausente em um pipeline gera resultado parcial, não falha
  agregada.** Em `causaganha_status`, um pipeline com `encontrado=False`
  aparece normalmente na lista (com contagens zeradas) — nunca derruba a
  tool inteira nem vira `ToolError`. Ausência de dado local é esperada, não
  excepcional.
- **`ultima_atualizacao` tem proveniência precisa, documentada por campo.**
  Três fontes possíveis, nunca combinadas silenciosamente: timestamp de uma
  entrada do manifest (`updated_at`, já presente em `SyncManifest`/
  `ManifestSTJ`/`ManifestJuris`; `ManifestDataJud` guarda o equivalente sob
  o nome `consultado_em` por entrada — `datajud_status` deriva
  `ultima_atualizacao` do máximo desses valores, não reintroduz outro nome),
  metadado de modificação do arquivo (`mtime`, só quando o manifest não
  guarda timestamp por entrada), ou o horário da própria consulta (caso de
  `datajud_facetas`, onde não existe manifest — daí o nome `consultado_em`
  no retorno dessa tool específica, não `ultima_atualizacao`, para deixar
  claro que é o instante da chamada, não de um dado persistido). Cada tool
  documenta explicitamente
  qual das três está usando; nunca apresentar `mtime` do arquivo local como
  se fosse "quando o pipeline rodou pela última vez" sem identificá-lo como
  tal.

## 4. Critérios de aceitação

**M1:**
- README com a seção de onboarding MCP: configuração stdio copiável para
  hosts com suporte a stdio local (ex.: Claude Desktop), nota separada de
  que ChatGPT exige implantação remota/túnel (não a mesma receita), cinco
  perguntas de exemplo.
- `title`/`description`/nomes de campo de todas as tools em português — em
  `parameters` (`diretorio_dados`, `caminho_manifesto`, `arquivo_manifesto`)
  tanto quanto em `output_schema`, com teste de schema exato cobrindo os
  dois lados (review da #854: a primeira versão só travava o output).
- Envelope `encontrado`/`ultima_atualizacao`/`fonte`/`canonica`/`aviso`
  presente e testado (schema exato) nas quatro tools locais; `consultado_em`
  + tribunal normalizado em `datajud_facetas`.
- `tjro_juris_status`/`stj_acordaos_status` usam `encontrado=False` para
  manifest ausente (paridade com `datajud_status`), não mais contagem zerada
  indistinguível de pipeline vazio.
- `causaganha_status` implementada, chamando `service.py` de cada pacote
  diretamente (teste que falha se algum dia importar `causaganha_mcp.tools`).
- Manifest ausente OU malformado em um pipeline não derruba
  `causaganha_status` — testado para os dois casos: falha de I/O (`OSError`)
  e conteúdo malformado (`ManifestFormatError`, nova classe em
  `tjro_juris.manifest`/`datajud.manifest`, que traduz o `KeyError`/
  `ValueError` de um `csv.DictReader` numa linha sem coluna esperada ou com
  número inválido — review da #854: a primeira versão só cobria I/O).
- `pytest`, `ruff check`, `ruff format --check` verdes.

**M2:**
- `scripts/reconcile_processos.py` publica `indice_processual.parquet` +
  `indice_processual.report.json` (cobertura por fonte); não publica mais
  `processos_unificados.parquet`/`processo_documentos.parquet` como
  arquivos.
- `scripts/render_queries.py` continua servindo `processos_multi_fonte.qmd`
  e os demais `.qmd` existentes sem mudança de contrato, recomputando
  `processos_unificados`/`processo_documentos` como views DuckDB a partir
  das fontes de origem.
- `causaganha.processos.cnj` é a única implementação Python de
  normalização/máscara de CNJ; `datajud.models` reexporta em vez de manter
  cópia própria.
- `causaganha.processos.service.buscar_processo` consulta
  `indice_processual.parquet` para descobrir fontes/URLs, depois os
  parquets de origem diretamente — nunca uma tabela pré-materializada; erro
  ao abrir o índice propaga (sem resposta possível), erro numa fonte
  específica ou no relatório de cobertura vira lacuna vazia + aviso em
  `avisos`, nunca exceção.
- `processo_consultar` registrada e testada (schema exato, comportamento
  com resultado encontrado/não-encontrado, tradução de exceção de domínio
  para `ToolError` sem vazar detalhe interno); `web_url` só quando
  `CAUSAGANHA_WEB_BASE_URL` está no ambiente.
- `web/src/lib/processoCnj.ts` + `ProcessoLookup.svelte` (dashboard
  `/processo`) migrados para o mesmo padrão de dois estágios (índice →
  parquets de origem) via DuckDB-WASM; nenhuma referência residual a
  `processos_unificados.parquet`/`processo_documentos.parquet` no
  frontend.
- `datajud.service`'s descoberta de CNJs lê `indice_processual.parquet`.
- Mesma disciplina de M1: fatos com proveniência, não veredito; `ToolError`
  estruturado para falha real, resultado parcial para ausência de dado.
- `pytest`, `ruff check`, `ruff format --check`, suíte de testes web
  (`npm test`) e `astro check` verdes.

## 5. Riscos

- **Uniformizar nomes de campo agora é mudança de schema deliberada, feita
  antes de haver consumidores reais do servidor.** Adiar isso até depois do
  onboarding (M1 é justamente o que cria os primeiros consumidores) seria
  quebra de compatibilidade num momento pior. Coberto com teste de schema
  exato por tool, não só ausência de campo credencial-like (padrão já
  existente em `test_tool_schema.py`, RFC 0013).
- **PT-BR nos textos exibidos ao host é uma escolha de produto, não
  universal.** Hosts MCP genéricos (não necessariamente usados só por
  brasileiros) podem preferir inglês. Aceito conscientemente: o produto e a
  base de usuários são brasileiros; nomes de função/módulo Python
  continuam em inglês, então o custo de reverter (se necessário) fica
  isolado nas strings de `title`/`description`/`Field(description=...)`.
- **M2 acabou maior do que "uma tool nova".** A investigação de fonte de
  dados levou a um redesenho do artefato canônico (`indice_processual
  .parquet` no lugar de `processos_unificados.parquet`/`processo_documentos
  .parquet`), que por sua vez toca o reconciliador, `render_queries.py`, a
  descoberta de CNJs do `datajud` e o dashboard web — quatro superfícies
  além da tool MCP em si. Aceito conscientemente (decisão explícita antes de
  começar a implementação, não descoberta no meio do trabalho): adiar o
  redesenho para depois de `processo_consultar` já existir teria criado uma
  segunda consumidora do formato antigo, tornando a migração posterior mais
  cara, não mais barata. `processos_unificados.parquet`/`processo_documentos
  .parquet` descontinuados como artefatos publicados nesta mesma PR — não
  há janela intermediária em que ambos os formatos precisam ser mantidos.
