# Plano — otimizar os Parquets consolidados para storage e leitura no IA

**Data:** 2026-06-07
**Contexto:** o schema de consolidação (10 tabelas, v`3.0.0`) já foi unificado em
uma única fonte (`schema_registry.py`). As colunas e tipos estão razoáveis, mas a
**camada física** dos Parquets gravados no Internet Archive não está otimizada
para o padrão de acesso real (DuckDB httpfs / WASM via HTTP Range requests).

Este plano ataca cada problema identificado na análise, em ordem de payoff.

## Como os dados chegam no IA hoje (baseline)

- **Item IA** = `djen-{tribunal}-{year}` (ex.: `djen-tjro-2025`). Uma run
  consolida *todos* os ZIPs de um (tribunal, ano) num DuckDB in-memory.
- **Um Parquet por tabela** → 10 arquivos por item; cada um contém o ano inteiro
  daquela tabela/tribunal.
- **Opções de escrita:** `COPY … (FORMAT PARQUET, COMPRESSION ZSTD,
  KV_METADATA {schema_version, item_id})`. Sem `ORDER BY`, sem `ROW_GROUP_SIZE`,
  sem `PARTITION_BY` (verificado em `scripts/pipeline/consolidate.py` e
  `src/causaganha/consolidate/exporter.py`).
- **Leitura:** DuckDB lê footer + row groups via HTTP Range.

Princípio orientador: **medir antes de migrar schema**. Mudanças de coluna são
caras (re-upload de itens no IA, bump de versão, quebra de consumidores
DuckDB-WASM). Mudanças de layout físico (ordenação, row-group size) são baratas e
não bumpam o schema.

**Legenda de evidência** (cada sub-item é marcado):

- **[verified]** — confirmado contra código ou comportamento real do DuckDB neste
  repo (com a linha/saída citada).
- **[benchmarked]** — medido com um experimento reproduzível (matriz/numeros neste
  doc).
- **[speculative]** — hipótese plausível, **ainda não medida**; não tratar como
  ganho provado até benchmarkar.

---

## Problema 1 — Row-group pruning está morto (maior payoff, sem bump) ⚠️

**Sintoma:** os dados são gravados em ordem de transform/hash. As estatísticas
min/max de cada row group abrangem quase o ano inteiro, então uma query por
`data_disponibilizacao` ou `numero_processo` precisa baixar **todos** os row
groups via Range. Paga-se por storage colunar e recebe-se I/O de full table scan.

**Fix:** layout físico, sem bump de schema. `1a` e `1b` são alavancas do `COPY`;
`1c` trata o caso do `numero_processo`, que **não** tem alavanca de `COPY` (ver
abaixo).

### 1a — `ORDER BY` na chave de filtro [verified que falta hoje]

- `comunicacoes` → **chave dominante conforme A0w** (uma chave física por arquivo):
  - se A0w mostrar **range por data** dominante → `.order_by(data_disponibilizacao, numero_processo)`
  - se A0w mostrar **lookup pontual por `numero_processo`** dominante →
    `.order_by(numero_processo, data_disponibilizacao)` (ou índice aditivo, §1c).
  - ⚠️ A chave **secundária só agrupa dentro da primária** — não dá pruning min/max
    global para o segundo predicado. Por isso a escolha da primária tem que vir de
    A0w, não ser fixa.
- `processos` → idem: `.order_by(data, numero_processo)` **ou** `(numero_processo, data)` conforme A0w
- `destinatarios` / `representacoes` / `comunicacao_advogados` → `.order_by(comunicacao_id)`
  (benefício é **pruning ao filtrar por `comunicacao_id`** — joins hash do DuckDB
  não exploram ordenação)
- `advogados` / `advogado_nomes` → `.order_by(nome)` ou `(uf_oab, numero_oab)`
- `classificacoes` → `.order_by(texto_id)`
- `textos` → `.order_by(id)` (acesso é por join em `id`)

### 1b — `ROW_GROUP_SIZE` explícito (tuning de granularidade, **não** pré-requisito) — [speculative, precisa benchmark]

⚠️ **`ORDER BY` sozinho já habilita pruning em arquivos com >1 row group.** Não
gate A1 nisto. O default do DuckDB é `ROW_GROUP_SIZE = 122_880` linhas: qualquer
arquivo **acima** desse tamanho já tem múltiplos row groups, então a ordenação
sozinha (A1) cria faixas min/max disjuntas e poda — sem tocar em `ROW_GROUP_SIZE`.
A1 é útil imediatamente; **não** depende do benchmark de A1b.

O caso onde `ORDER BY` **não muda nada** [verified] é o item **pequeno** que cabe
num **único** row group (ex.: `djen-tjro-2025`): há um só row group cobrindo o ano
todo e um Range read baixa tudo. `ROW_GROUP_SIZE` menor não ajuda esse caso (o
arquivo já é pequeno) — ele serve para **ajustar a granularidade** dos itens
grandes, onde row groups menores dão faixas min/max mais estreitas, **mas com
custo**: mais overhead de footer e possível **piora de full scans** (mais row
groups para varrer). O valor `16_384` citado antes **não é um default seguro** — é
só um ponto de partida.

**Antes de fixar o valor, rodar um benchmark** [speculative até medir]: comparar
`16K`, `32K`, `64K` e o default (`122_880`) contra arquivos de produção reais,
medindo **separadamente** queries seletivas e full scans, e reportando por caso:
contagem de row groups, tamanho do arquivo, bytes lidos via httpfs e wall-clock.
Escolher o **menor** size que dá ganho de pruning mensurável **sem** degradar o
broad scan. Validar só o `parquet_metadata` (faixas) cobre o lado do pruning, não
o lado do custo.

### 1c — Lookup pontual por `numero_processo`: escolher a chave de ordenação

O outro acesso quente é por `numero_processo` (CNJ de 20 dígitos, alta entropia).
Ordenar por `data_disponibilizacao` **não** agrupa o `numero_processo`, então
min/max não podam nada para esse acesso — e **não dá para ordenar fisicamente o
mesmo arquivo por duas chaves**. Há um trade-off de uma-chave-por-arquivo.

⚠️ **Bloom filter via `COPY` não ajuda *esta* coluna — por cardinalidade, não por
falta de suporte.** [benchmarked, DuckDB 1.5.3 fixado no repo] Correção de uma
afirmação anterior cedo demais: o DuckDB **escreve** bloom filters de Parquet, mas
só para colunas **dictionary-encoded** (baixa cardinalidade). Não existe sintaxe
por coluna (`BLOOM_FILTER(col)` é rejeitada); o flag global é
`WRITE_BLOOM_FILTER true`. Matriz medida — **500K linhas** fixas, coluna CNJ
zero-padded de 20 dígitos, variando a cardinalidade (≤ nº de linhas). Script
reproduzível: `scripts/benchmarks/bloom_cardinality.py`:

| cardinalidade (distintos) | bloom escrito? |
|---|---|
| 100 | **sim** |
| 100_000 | não |
| 500_000 (≈ único) | não |

`numero_processo` é **alta cardinalidade** (quase único por linha) → o DuckDB não
dictionary-encoda → **não escreve bloom filter** para ele. Ou seja: bloom filter é
inútil **para esta coluna pela natureza do dado**, não porque o DuckDB não saiba
escrever. Forçá-lo exigiria dictionary encoding manual ou outro writer (ex.:
pyarrow) — fora do quick-win sem bump. (Chaves de join de menor cardinalidade
*podem* receber bloom filter; medir caso a caso se virar gargalo.)

Estratégia realista, em ordem:

1. **Ordenar `comunicacoes` pela chave dominante** (provavelmente
   `data_disponibilizacao`, confirmar com os logs de query do dashboard). O outro
   acesso paga full-scan de row groups.
2. **Se o lookup por `numero_processo` for hot o suficiente**, criar um Parquet
   aditivo (índice) ordenado por `numero_processo` — mesmo padrão do serving do
   Problema 3 — para que min/max podem por esse acesso. Por ser um **dataset novo
   com schema e contrato de consumidor próprios**, leva um **bump aditivo** (igual
   ao serving — agrupar no mesmo `3.1.0`) e tem que ser **registrado** junto às
   demais tabelas (schema registry + tooling de validação/descoberta), senão
   clientes não têm como saber se o índice existe. Não é "sem bump".
3. A migração `numero_processo` para um **encoding empacotado** (Problema 2 / A3)
   **reduz bytes** — mas **não** melhora a seletividade de min/max. Para CNJs como
   strings de 20 dígitos zero-padded, a ordem lexicográfica já é idêntica à
   numérica, então min/max poda igual com ou sem empacotamento; o ganho de pruning
   vem da **ordenação/índice** (§1a-1b), não do encoding. O encoding só vale por
   tamanho, e só se for empacotado de verdade:

   - `string→BLOB` genérico mantém os 20 bytes ASCII (no-op).
   - **`HUGEINT`/`UHUGEINT` NÃO servem** (verificado no DuckDB 1.5.3): o `COPY`
     mapeia ambos para Parquet `DOUBLE`, então `99999999999999999999` volta como
     `1e+20` — **perde precisão**.
   - **Usar `DECIMAL(20,0)`**: o `COPY` grava como `FIXED_LEN_BYTE_ARRAY` (~16
     bytes < 20 ASCII) e faz round-trip lossless (verificado). Alternativa: byte
     array de largura fixa com encoding explícito.
   - **Exigir um teste de round-trip** (`COPY` → `read_parquet` → comparar com o
     original) antes de fechar a migração; decode no consumidor (DuckDB-WASM) faz
     parte da tarefa.

   **Validar o formato antes (parte do A0):** o encoding numérico assume 20
   dígitos, mas `_safe()` (ambos os code paths) converte valores ausentes em `''`
   e `validate_ndjson_sample()` só checa presença, não formato (os testes aceitam
   `numero_processo: "x"`). Valores históricos não-numéricos/curtos fazem o cast
   `DECIMAL` falhar. O A0 tem que auditar essa invariante e a migração tem que
   definir um **fallback reversível** — reter o `numero_processo` original como
   string (campo companheiro/variante) para os não-conformes. **Não** usar
   sentinela: colapsa valores distintos, pode colidir com um válido e impede
   reconstruir o original, quebrando a promessa lossless.

**Onde:** o `COPY` é montado em `scripts/pipeline/consolidate.py:1419-1424` e
`src/causaganha/consolidate/exporter.py:57-62` (acrescentar as opções ao
`copy_opts`); o `ORDER BY` vai nos builders `_build_*` de
`scripts/pipeline/consolidate.py` **e** de
`src/causaganha/consolidate/transforms.py` (lógica forkada — mudar nos dois). A
ordenação é uma expressão Ibis lazy — o DuckDB aplica no `COPY` final, sem
materializar em Python.

**Validação (dois níveis):**

1. **Estrutural:** `SELECT stats_min, stats_max FROM
   parquet_metadata('comunicacoes.parquet')` deve mostrar faixas estreitas e
   disjuntas de `data_disponibilizacao` por row group (e >1 row group nos itens
   grandes).
2. **I/O real (prova do payoff):** medir bytes baixados via httpfs para uma query
   representativa do dashboard (`SET enable_http_metadata_cache=true; …`)
   pré/pós. Faixas estreitas no metadata são necessárias mas não suficientes — só
   o byte-count prova que "baixa 1 row group vs. o ano todo".

**Schema bump:** não (A1/A1b). **Esforço:** P (`ORDER BY`) + P-M (benchmark de
row-group); índice aditivo por `numero_processo` é M. **Payoff:** Grande **para
itens grandes**; neutro para itens pequenos de 1 row group. **[A1 verified como
faltante; A1b speculative até benchmarkar.]**

---

## Problema 2 — Chaves UUID gravadas como string de 36 chars (maior custo de tamanho) ⚠️

**Sintoma:** o schema é UUID-keyed em todo lugar (`id`, `original_id`,
`texto_id`, `comunicacao_id`, `advogado_id`, `parte_id`,
`winner_advogado_id`, `loser_advogado_id`), todos `string`. Um UUIDv5 em texto
são 36 bytes de alta entropia → dictionary/ZSTD rendem pouco. Em binário
(`UUID`/16-byte fixed ou `BLOB`) são ~16 bytes e codificam melhor.

**Pré-requisito (NÃO migrar às cegas):** medir primeiro (ver tarefa A0). Decidir
com base em dado:

- Se as chaves UUID dominam os bytes não-texto → migração vale.
- Se `texto` domina → pular (o ganho é ruído).
- **Não esquecer `numero_processo`:** é uma string CNJ de 20 dígitos, alta
  entropia, presente em `comunicacoes` e `processos` [verified — não existe em
  `destinatarios`, cujo identificador é `comunicacao_id`]. Pode pesar **mais** que
  os UUIDs nos bytes não-texto. A medição A0 tem que reportá-la lado
  a lado com as chaves UUID — senão a decisão fica com visão de túnel no UUID e
  ignora a coluna que talvez seja o maior alvo. **Atenção:** ao contrário do UUID
  (que já é 16 bytes em binário), o CNJ só ganha **bytes** (não pruning) e precisa
  de um **encoding empacotado explícito** — `string→BLOB` é no-op e `HUGEINT` vira
  `DOUBLE` (perde precisão). Ver §1c passo 3 para a representação correta
  (`DECIMAL(20,0)`), o round-trip e o fallback de formato.

**Fix (se confirmado):** mudar UUIDs de `string` → tipo binário no registry.
Isto é um **bump major (4.0.0)** e força todo consumidor DuckDB-WASM a `decode`.
Implementação:

1. `schema_registry.py`: nova `SCHEMA_V4` com chaves binárias; `CURRENT_VERSION`.
2. Builders: `djen_uuid5(...)` retorna binário 16-byte em vez de string.
3. `validation.py`: invariantes de tipo atualizadas.
4. Zod/frontend: schema `v4` + decode helper.
5. Reconsolidação seletiva (datas `schema_version < CURRENT`).

**Schema bump:** sim (major). **Esforço:** M. **Payoff:** Grande *se* medição confirmar.

---

## Problema 3 — JOINs cross-file pagam latência HTTP por arquivo

**Sintoma:** 10 tabelas normalizadas são limpas como forma canônica, mas o
DuckDB-over-HTTP paga footer + Range reads por arquivo a cada JOIN. A query
"advogado → comunicações com outcome" é um join de 4 tabelas
(`comunicacao_advogados` × `comunicacoes` × `classificacoes` × `advogados`).

> ⚠️ **Ressalva (verificado no código):** esse join de 4 tabelas **ainda não
> existe** no frontend. O consumidor atual é `web/src/components/
> DuckDBExplorer.svelte`, que opera sobre **um** item `(tribunal, ano)` por vez,
> sem `union_by_name` cross-item; o template "advogados mais ativos" faz no
> máximo um join de **2** tabelas (`advogados` × `comunicacao_advogados`) e as
> classificações são consultadas à parte. Portanto o serving **não elimina 3
> leituras de um load path existente** — ele *habilita* um fluxo planejado. O
> payoff é condicional a construir esse consumidor; sem ele, é storage extra sem
> retorno. É a Trilha B (product-gated), não o caminho crítico de storage.

**Fix:** Parquet-per-access-pattern (ficha ADR 0008). Manter as 10 tabelas
normalizadas como **canônicas** e adicionar um Parquet de **serving**
denormalizado, modelado na query quente:

```
serving_advogado_comunicacoes.parquet
  advogado_id, advogado_nome, numero_oab, uf_oab,
  comunicacao_id, numero_processo, data_disponibilizacao, tribunal,
  outcome, decision_type, confidence
  (ordenado por advogado_id, data_disponibilizacao)
```

Gerado no fim da consolidação a partir das tabelas canônicas (uma expressão Ibis
de join: `comunicacao_advogados` × `comunicacoes` × `classificacoes` [via
`texto_id`] × `advogados`). As colunas de outcome existem em `classificacoes`
(`outcome`, `decision_type`, `confidence` — verificado no `schema_registry.py`),
então o serving é puro join, sem coluna nova derivada.

**Escopo do arquivo:** o serving é **por item** `(tribunal, ano)`, igual às
canônicas. Seria 1 arquivo em vez de 4 **por item** — não um arquivo global
único.

**Pré-requisito honesto:** esta tarefa só tem payoff se vier acompanhada do
**fluxo de consumo** que faz o join de 4 tabelas (hoje inexistente — ver ressalva
acima). Planejar os dois juntos ou não priorizar.

**Schema bump:** patch (tabela nova, aditiva — `3.1.0`). **Esforço:** M (Parquet)
+ M (consumidor no frontend). **Payoff:** Grande **se** o consumidor for
construído; nulo isolado.

---

## Problema 4 — Colunas constantes redundantes por arquivo

**Sintoma:** como o item é um (tribunal, ano), `tribunal`, `p_ano` e
`p_item_ia` são **constantes** dentro de cada arquivo. ZSTD+RLE comprime para
quase nada (custo de storage desprezível), mas são ruído de schema e `p_item_ia`
duplica info já presente no `KV_METADATA` (footer) e no nome do arquivo.

**Fix:**

- Manter `tribunal` e `p_ano` — queries cross-item (`union_by_name`) usam para
  filtrar/agrupar.
- `p_item_ia`: **candidato a remoção, não remoção certa.** A info já está em
  `kv_metadata.causaganha.item_id` (footer) e no path do item. **Mas:** o ganho de
  storage é provavelmente ínfimo (a própria análise diz que comprime "para quase
  nada" via RLE), e remover troca um **campo queryable** por algo que o consumidor
  teria que reconstruir do footer/path — é mudança de schema/API, não limpeza
  pura. **Pré-requisito:** auditar consumidores (frontend, scripts, queries `.qmd`,
  debugging ad-hoc) e só remover se nenhum usar `p_item_ia` como coluna. Se
  remover, documentar quais workflows perdem o acesso direto e como recuperam a
  proveniência (ler `kv_metadata`).

**Schema bump:** sim (major — remoção de coluna), **se** a auditoria liberar.
Agrupar com o Problema 2 no mesmo `4.0.0` para não pagar dois re-uploads.
**Esforço:** P. **Payoff:** Pequeno (storage ínfimo; o valor real é só reduzir
ruído de schema).

---

## Problema 5 — Ajustes finos de tipo

**Sintoma:** ganhos pequenos, agrupar com outro bump.

- `confidence` `float64` → `float32` (confiança não precisa de precisão dupla).
- `hash` é texto de alta cardinalidade que comprime mal — avaliar se precisa
  viver no store colunar, ou se pode ser binário como os UUIDs.

**Schema bump:** sim — juntar com `4.0.0`. **Esforço:** P. **Payoff:** Pequeno.

---

## Ordem de execução

Duas trilhas independentes. **A** é trabalho de storage validável (medir → aplicar
→ provar). **B** é feature de produto especulativa, **gated** por um consumidor que
ainda não existe — não fica no caminho crítico de storage.

### Trilha A — storage validado (storage roadmap)

| # | Tarefa | Bump? | Esforço | Payoff |
|---|--------|-------|---------|--------|
| A0 | Medição **de storage**: baixar **vários** itens (tribunais/anos de tamanhos diferentes) do IA + `parquet_metadata()` por coluna, em **todas** as tabelas largas. Reportar bytes por coluna (UUIDs **e** `numero_processo`), cardinalidade, e **auditar o formato de `numero_processo`** (quantos não são 20 dígitos) | não | P | Habilita A0e/A4/A5 |
| A0w | Medição **de workload** (gate de A1): coletar a frequência de query por predicado — `data_disponibilizacao` (range) vs `numero_processo` (pontual) — dos logs do dashboard/explorador. A1 ordena por **uma** chave; ordenar pela errada deixa a outra em full-scan. Sem essa evidência, **não** escolher a chave de A1 — ou benchmarkar os dois workloads. | não | P | **Gate de A1** |
| A0e | Benchmark **de encoding** (gate de A2/A3): nos mesmos itens representativos de A0, rodar `COPY` **lado a lado** do schema atual vs candidato (`VARCHAR`→16-byte UUID; `VARCHAR`→`DECIMAL(20,0)`) e comparar os **bytes comprimidos reais por coluna** (com ZSTD + dictionary, como em produção). Dominar o tamanho atual (A0) **não** prova economia — dictionary/ZSTD podem comprimir a string bem mais (ou menos) que o delta de largura crua sugere. **Gate:** só seguir com A2/A3 se a economia medida justificar o re-upload major. | não | P-M | **Gate de A2/A3** |
| A1 | Layout físico no `COPY` (ambos os code paths): **1a** `ORDER BY` pela chave dominante **identificada em A0w**. [verified que falta hoje] | não | P | **Grande** (itens grandes) |
| A1b | Benchmark de `ROW_GROUP_SIZE` (16K/32K/64K/default) em arquivos reais: seletivas vs full scan, bytes httpfs + wall-clock; fixar o menor size sem degradar scan. [speculative até medir] | não | P-M | Grande se confirmado |
| A2 | (se **A0e** confirmar economia, não só dominância em A0) UUID `string → 16-byte` no registry. **Contrato WASM:** ler `BLOB`/`UUID` 16-byte → `uuid.stringify`. **Pré-req de rollback (A-pré):** ver nota abaixo | major `4.0.0` | M | Grande |
| A3 | (se **A0e** confirmar economia, não só dominância em A0) CNJ `string → DECIMAL(20,0)`. [verified: BLOB é no-op; HUGEINT vira DOUBLE/perde precisão; `DECIMAL(20,0)` round-trips]. **Só ganha bytes, não pruning.** Exige round-trip test + **fallback reversível** (string companheira p/ não-conformes) + decode no WASM. **Pré-req de rollback (A-pré)** | major `4.0.0` | M | Médio |
| A4 | (se auditoria de consumidores liberar) remover `p_item_ia` | major `4.0.0` | P | Pequeno |
| A5 | `confidence`→float32; revisar `hash` (binário?) | major `4.0.0` | P | Pequeno |

A2-A5 agrupam-se num único bump `4.0.0` (cada major força re-upload de todos os
itens; não pagar dois).

**Caminho crítico de A:** A0 + A0w → A1 → A-pré → A0e → (A2+A3+A4+A5). **A1b fica
fora do caminho crítico** — é tuning independente (§1b) e roda **em paralelo**; as
economias de schema (A2-A5) são gated por A0e (economia medida), não por A0 sozinho
nem por `ROW_GROUP_SIZE`. Se nenhum size menor evitar regressão de broad-scan, A1b
simplesmente mantém o default e a migração v4 segue mesmo assim.

> **A-pré — artefato de rollback (pré-requisito de A2/A3, hoje inexistente).** O
> rollback "reler a versão anterior" **não existe no pipeline atual**:
> `export_table_sync()` sempre grava `{table}.parquet` e `_upload_consolidated()`
> sobe esse mesmo nome **dentro do mesmo item IA** `djen-{tribunal}-{ano}`; o
> manifest de consolidação só registra a versão corrente. Quando o v4 sobrescreve
> os arquivos, **não sobra URL endereçável por versão** do v3 para reler — a
> imutabilidade-por-versão que eu havia afirmado é falsa. Antes de prometer
> rollback, implementar **uma** destas: (a) nomes de arquivo versionados
> (`{table}-v4.parquet`), (b) itens versionados (`djen-{tribunal}-{ano}-v4`), ou
> (c) um procedimento explícito de restauração (snapshot do v3 antes do
> re-upload). Sem isso, A2/A3 são **irreversíveis** na prática.

### Trilha B — serving/consumidor (product-gated, opcional)

| # | Tarefa | Bump? | Depende de | Payoff |
|---|--------|-------|-----------|--------|
| B1 | **Decisão de produto:** construir o fluxo frontend "advogado → comunicações com outcome" (join de 4 tabelas, hoje inexistente) | — | priorização de produto | habilita B2 |
| B2 | Parquet de serving denormalizado | patch `3.1.0` | **B1** | Grande **só** com B1 |

B só vale com B1. **Sem B1, não fazer B2** — seria storage extra sem consumidor.
Não é pré-requisito de nenhum item da Trilha A.

**Quick win imediato:** A1 — `ORDER BY` sozinho **já** poda em arquivos com >1 row
group (itens grandes), sem depender de A1b. `ROW_GROUP_SIZE` **não** é exclusivo do
item pequeno: ele muda a **granularidade de pruning, o overhead de footer e o
comportamento de scan dos arquivos grandes** que já têm múltiplos grupos — é
justamente por isso que A1b mira esses itens; e, num arquivo pequeno, pode
**quebrá-lo em vários grupos**. O único caso onde a **ordenação** (A1) é no-op
[verified] é o item pequeno de 1 row group. Não dá para cobrir
`data_disponibilizacao` *e* `numero_processo` na mesma ordenação — escolher a chave
dominante **via A0w** e, se preciso, um índice aditivo (bloom filter não cobre essa
coluna por cardinalidade, §1c). Provar o ganho com byte-count httpfs, não só com
`parquet_metadata`.

## O que NÃO fazer

- **Não migrar UUID nem CNJ sem medir (A0).** São decisões **separadas** (formas de
  dado diferentes). Se `texto` domina os bytes, o ganho é ruído e o custo (bump
  major + decode no WASM) não compensa. Medir várias tabelas, UUIDs **e**
  `numero_processo`, senão a decisão fica enviesada.
- **Não confiar em `ORDER BY` sozinho (A1).** Sem `ROW_GROUP_SIZE`, itens
  pequenos ficam com 1 row group e a ordenação não poda nada. **E não fixar 16K
  como default** — benchmarkar (A1b) o custo de full scan, não só o pruning.
  Validar com byte-count httpfs, não só com `parquet_metadata`.
- **Não contar com bloom filter de Parquet para `numero_processo` (§1c).**
  [benchmarked] O DuckDB escreve bloom filter, mas só p/ colunas dictionary-encoded
  (baixa cardinalidade); CNJ é alta cardinalidade → não recebe. Não planejar poda
  de lookup pontual em cima disso para esta coluna.
- **Não fazer o serving (B2) sem o consumidor (B1).** O join de 4 tabelas não
  existe no frontend hoje; sem construí-lo, o serving é só storage extra. É trilha
  separada, não caminho crítico de storage.
- **Não reshapear as 10 tabelas canônicas** para o serving. Adicionar Parquet
  aditivo; manter o modelo normalizado como fonte.
- **Não remover `p_item_ia` sem auditar consumidores (A4).** Storage ganho é
  ínfimo; é troca de campo queryable por reconstrução via footer/path.
- **Não fazer dois bumps majors separados.** Agrupar A2-A5 em `4.0.0` —
  cada bump força re-upload de todos os itens no IA (sem update parcial).
- **Não esquecer o code path legado.** `consolidate-parquet.yml` roda
  `scripts/pipeline/consolidate.py`; toda mudança de layout precisa estar lá
  *e* em `transforms.py`/`exporter.py` (hoje os schemas já são compartilhados via
  registry, mas a lógica de `ORDER BY`/serving é por-builder).
