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

---

## Problema 1 — Row-group pruning está morto (maior payoff, sem bump) ⚠️

**Sintoma:** os dados são gravados em ordem de transform/hash. As estatísticas
min/max de cada row group abrangem quase o ano inteiro, então uma query por
`data_disponibilizacao` ou `numero_processo` precisa baixar **todos** os row
groups via Range. Paga-se por storage colunar e recebe-se I/O de full table scan.

**Fix:** três alavancas físicas no `COPY`, todas sem bump de schema:

### 1a — `ORDER BY` na chave de filtro

- `comunicacoes` → `.order_by(data_disponibilizacao, numero_processo)`
- `processos` → `.order_by(data, numero_processo)`
- `destinatarios` / `representacoes` / `comunicacao_advogados` → `.order_by(comunicacao_id)`
  (benefício é **pruning ao filtrar por `comunicacao_id`** — joins hash do DuckDB
  não exploram ordenação)
- `advogados` / `advogado_nomes` → `.order_by(nome)` ou `(uf_oab, numero_oab)`
- `classificacoes` → `.order_by(texto_id)`
- `textos` → `.order_by(id)` (acesso é por join em `id`)

### 1b — `ROW_GROUP_SIZE` explícito (pré-requisito para o `ORDER BY` valer)

⚠️ **Ordenar sozinho pode ser no-op.** O pruning só existe quando o arquivo tem
**mais de um row group**. O default do DuckDB é `ROW_GROUP_SIZE = 122_880`
linhas. Um item pequeno `(tribunal, ano)` (ex.: `djen-tjro-2025`) cabe inteiro
num único row group — nesse caso `ORDER BY` **não muda nada**, porque há um só
row group cobrindo o ano todo e um único Range read baixa tudo de qualquer jeito.

Adicionar `ROW_GROUP_SIZE` menor (ex.: 16_384) ao `COPY` para que a ordenação
produza faixas min/max **disjuntas**. Para itens grandes (TJSP) isso multiplica os
row groups e habilita o pruning; para itens pequenos é inócuo (continua 1 row
group, mas o arquivo já é pequeno).

### 1c — Lookup pontual por `numero_processo`: escolher a chave de ordenação

O outro acesso quente é por `numero_processo` (CNJ de 20 dígitos, alta entropia).
Ordenar por `data_disponibilizacao` **não** agrupa o `numero_processo`, então
min/max não podam nada para esse acesso — e **não dá para ordenar fisicamente o
mesmo arquivo por duas chaves**. Há um trade-off de uma-chave-por-arquivo.

> ⚠️ **Bloom filter via `COPY` NÃO é uma opção (verificado empiricamente no
> DuckDB 1.5.3 fixado no repo).** Não existe sintaxe por coluna — `COPY … (FORMAT
> PARQUET, BLOOM_FILTER(numero_processo))` é rejeitado como opção desconhecida. O
> flag global `WRITE_BLOOM_FILTER true` é *aceito mas no-op*: `bloom_filter_offset`
> continua `NULL` no `parquet_metadata`, o arquivo fica byte-idêntico ao escrito
> sem o flag, e `parquet_bloom_probe` não encontra nada. Subir o piso do DuckDB
> não resolve. Escrever bloom filter exigiria outro writer (ex.: pyarrow) — fora
> do quick-win sem bump.

Estratégia realista, em ordem:

1. **Ordenar `comunicacoes` pela chave dominante** (provavelmente
   `data_disponibilizacao`, confirmar com os logs de query do dashboard). O outro
   acesso paga full-scan de row groups.
2. **Se o lookup por `numero_processo` for hot o suficiente**, criar um Parquet
   aditivo (índice) ordenado por `numero_processo` — mesmo padrão do serving do
   Problema 3 — para que min/max podem por esse acesso. Aditivo, sem bump.
3. A migração `numero_processo` para um **encoding empacotado** (Problema 2 / #3)
   reduz bytes e melhora a seletividade de min/max independentemente da ordenação
   — **mas só se for empacotado de verdade.** `string→BLOB` genérico mantém os
   mesmos 20 bytes ASCII (no-op). Definir a representação lossless antes: o CNJ é
   numérico de 20 dígitos, cujo máximo (~10²⁰) estoura `int64` (2⁶³≈9,2·10¹⁸), então
   precisa de inteiro 128-bit / 16-byte fixo (16 < 20 bytes) e a reconstrução
   re-aplica zero-pad para 20 dígitos. Decodificação no consumidor (DuckDB-WASM)
   faz parte da tarefa.

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

**Schema bump:** não. **Esforço:** P (1a/1b); 1c-opção-2 é M (Parquet de índice
aditivo). **Payoff:** Grande **para itens grandes**; neutro para itens pequenos de
1 row group.

---

## Problema 2 — Chaves UUID gravadas como string de 36 chars (maior custo de tamanho) ⚠️

**Sintoma:** o schema é UUID-keyed em todo lugar (`id`, `original_id`,
`texto_id`, `comunicacao_id`, `advogado_id`, `parte_id`,
`winner_advogado_id`, `loser_advogado_id`), todos `string`. Um UUIDv5 em texto
são 36 bytes de alta entropia → dictionary/ZSTD rendem pouco. Em binário
(`UUID`/16-byte fixed ou `BLOB`) são ~16 bytes e codificam melhor.

**Pré-requisito (NÃO migrar às cegas):** medir primeiro (ver tarefa #0). Decidir
com base em dado:

- Se as chaves UUID dominam os bytes não-texto → migração vale.
- Se `texto` domina → pular (o ganho é ruído).
- **Não esquecer `numero_processo`:** é uma string CNJ de 20 dígitos, alta
  entropia, repetida em `comunicacoes`/`processos`/`destinatarios`. Pode pesar
  **mais** que os UUIDs nos bytes não-texto. A medição #0 tem que reportá-la lado
  a lado com as chaves UUID — senão a decisão fica com visão de túnel no UUID e
  ignora a coluna que talvez seja o maior alvo. **Atenção:** ao contrário do UUID
  (que já é 16 bytes em binário), o CNJ precisa de um **encoding empacotado
  explícito** — `string→BLOB` genérico é no-op (mantém 20 bytes ASCII). Ver §1c
  passo 3 para a representação (inteiro 128-bit, zero-pad na reconstrução).

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
> retorno. Não priorizar #2 acima de #1 só por esse "payoff de latência".

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
- Remover `p_item_ia` das tabelas: já está em `kv_metadata.causaganha.item_id` e
  no path do item. Leitores que precisam podem ler do footer.

**Schema bump:** sim (major — remoção de coluna). Agrupar com o Problema 2 no
mesmo `4.0.0` para não pagar dois re-uploads. **Esforço:** P. **Payoff:** Pequeno.

---

## Problema 5 — Ajustes finos de tipo

**Sintoma:** ganhos pequenos, agrupar com outro bump.

- `confidence` `float64` → `float32` (confiança não precisa de precisão dupla).
- `hash` é texto de alta cardinalidade que comprime mal — avaliar se precisa
  viver no store colunar, ou se pode ser binário como os UUIDs.

**Schema bump:** sim — juntar com `4.0.0`. **Esforço:** P. **Payoff:** Pequeno.

---

## Ordem de execução

| # | Tarefa | Bump? | Esforço | Payoff |
|---|--------|-------|---------|--------|
| 0 | Script de medição: baixar **vários** itens (tribunais/anos de tamanhos diferentes) do IA + `parquet_metadata()` por coluna, em **todas** as tabelas largas, reportando `numero_processo` ao lado das chaves UUID | não | P | Habilita decisões 2/5 |
| 1 | Layout físico no `COPY` (ambos os code paths): **1a** `ORDER BY` + **1b** `ROW_GROUP_SIZE`, com benchmark de bytes httpfs pré/pós. (**1c** lookup por `numero_processo`: escolher chave de ordenação / índice aditivo — bloom filter via `COPY` não funciona, ver §1c) | não | P | **Grande** (itens grandes) |
| 2 | Parquet de serving denormalizado — **só junto** com o consumidor frontend (join de 4 tabelas hoje inexistente) | patch `3.1.0` | M+M | Grande **se** consumidor construído |
| 3 | (se #0 confirmar) UUID `string→16-byte` + `numero_processo` para inteiro 128-bit empacotado (BLOB genérico é no-op; definir encoding lossless + decode no WASM) | major `4.0.0` | M | Grande |
| 4 | Remover `p_item_ia` redundante | major `4.0.0` | P | Pequeno |
| 5 | `confidence`→float32, revisar `hash` | major `4.0.0` | P | Pequeno |

**Caminho crítico:** 0 → 1 → 2 → (3+4+5 num único bump 4.0.0).

**Quick win imediato:** #1 — mas atenção: `ORDER BY` **sozinho é no-op** em itens
de 1 row group; só vira "baixar 1 row group vs. o ano inteiro" quando casado com
`ROW_GROUP_SIZE` (1b). Não dá para cobrir `data_disponibilizacao` *e*
`numero_processo` na mesma ordenação, e bloom filter via `COPY` não funciona no
DuckDB fixado (§1c) — escolher a chave dominante e, se preciso, um índice aditivo.
Prove o ganho com o byte-count httpfs, não só com `parquet_metadata`.

## O que NÃO fazer

- **Não migrar UUID para binário sem medir (#0).** Se `texto` domina os bytes, o
  ganho é ruído e o custo (bump major + decode no WASM) não compensa. E não medir
  só `comunicacoes`/só UUIDs — incluir `numero_processo` e várias tabelas, senão a
  decisão fica enviesada.
- **Não confiar em `ORDER BY` sozinho (#1).** Sem `ROW_GROUP_SIZE`, itens
  pequenos ficam com 1 row group e a ordenação não poda nada. Validar com
  byte-count httpfs, não só com `parquet_metadata`.
- **Não contar com bloom filter de Parquet via `COPY` (#1c).** Verificado no
  DuckDB 1.5.3 do repo: sintaxe por coluna é rejeitada e `WRITE_BLOOM_FILTER` é
  no-op. Não planejar a poda de lookup pontual em cima disso.
- **Não priorizar o serving (#2) como ganho de latência sem o consumidor.** O join
  de 4 tabelas não existe no frontend hoje; sem construí-lo, o serving é só
  storage extra.
- **Não reshapear as 10 tabelas canônicas** para o serving. Adicionar Parquet
  aditivo; manter o modelo normalizado como fonte.
- **Não fazer dois bumps majors separados.** Agrupar 3, 4 e 5 em `4.0.0` —
  cada bump força re-upload de todos os itens no IA (sem update parcial).
- **Não esquecer o code path legado.** `consolidate-parquet.yml` roda
  `scripts/pipeline/consolidate.py`; toda mudança de layout precisa estar lá
  *e* em `transforms.py`/`exporter.py` (hoje os schemas já são compartilhados via
  registry, mas a lógica de `ORDER BY`/serving é por-builder).
