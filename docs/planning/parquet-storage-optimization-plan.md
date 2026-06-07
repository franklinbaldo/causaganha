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

### 1c — Bloom filter em `numero_processo` (lookup pontual)

O lookup quente do dashboard é por `numero_processo` (CNJ de 20 dígitos, alta
entropia). Ordenar por `data_disponibilizacao` **não** agrupa o `numero_processo`,
então min/max não podam nada para esse acesso. O writer Parquet do DuckDB
suporta bloom filters por coluna — eles podam row groups em lookups de igualdade
muito melhor que min/max. Adicionar bloom filter em `numero_processo` (e nas
chaves de join, se a medição #0 mostrar que ajuda).

> **Requisito de versão:** escrita de bloom filter Parquet precisa de **DuckDB
> ≥ 1.1**. O `pyproject.toml` hoje fixa `duckdb>=0.10.0` — subir o piso (ou
> detectar a versão e degradar 1c graciosamente) é parte desta tarefa. `ORDER BY`
> e `ROW_GROUP_SIZE` funcionam em 0.10.

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

**Schema bump:** não. **Esforço:** P (1a/1b) + P (1c). **Payoff:** Grande **para
itens grandes**; neutro para itens pequenos de 1 row group.

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
  ignora a coluna que talvez seja o maior alvo.

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
DuckDB-over-HTTP paga footer + Range reads por arquivo a cada JOIN. O hot path do
dashboard ("advogado → comunicações com outcome") é um join de 4 tabelas
(`comunicacao_advogados` × `comunicacoes` × `classificacoes` × `advogados`)
executado por HTTP a cada load.

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
canônicas. Lê-se 1 arquivo em vez de 4 **por item** — mas o frontend continua
fazendo `union_by_name` entre itens para visões cross-tribunal/ano. Não é um
arquivo global único; o ganho é eliminar 3 footers + N Range reads por item a
cada load.

**Schema bump:** patch (tabela nova, aditiva — `3.1.0`). **Esforço:** M. **Payoff:** Grande para latência do frontend.

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
| 1 | Layout físico no `COPY` (ambos os code paths): **1a** `ORDER BY` + **1b** `ROW_GROUP_SIZE` + **1c** bloom filter em `numero_processo`, com benchmark de bytes httpfs pré/pós | não | P | **Grande** (itens grandes) |
| 2 | Parquet de serving denormalizado para o hot path | patch `3.1.0` | M | Grande (frontend) |
| 3 | (se #0 confirmar) UUID + `numero_processo` `string→binary` | major `4.0.0` | M | Grande |
| 4 | Remover `p_item_ia` redundante | major `4.0.0` | P | Pequeno |
| 5 | `confidence`→float32, revisar `hash` | major `4.0.0` | P | Pequeno |

**Caminho crítico:** 0 → 1 → 2 → (3+4+5 num único bump 4.0.0).

**Quick win imediato:** #1 — mas atenção: `ORDER BY` **sozinho é no-op** em itens
de 1 row group; só vira "baixar 1 row group vs. o ano inteiro" quando casado com
`ROW_GROUP_SIZE` (1b). Para o lookup por `numero_processo`, o bloom filter (1c)
vale mais que a ordenação. Prove o ganho com o byte-count httpfs, não só com
`parquet_metadata`.

## O que NÃO fazer

- **Não migrar UUID para binário sem medir (#0).** Se `texto` domina os bytes, o
  ganho é ruído e o custo (bump major + decode no WASM) não compensa. E não medir
  só `comunicacoes`/só UUIDs — incluir `numero_processo` e várias tabelas, senão a
  decisão fica enviesada.
- **Não confiar em `ORDER BY` sozinho (#1).** Sem `ROW_GROUP_SIZE`, itens
  pequenos ficam com 1 row group e a ordenação não poda nada. Validar com
  byte-count httpfs, não só com `parquet_metadata`.
- **Não reshapear as 10 tabelas canônicas** para o serving. Adicionar Parquet
  aditivo; manter o modelo normalizado como fonte.
- **Não fazer dois bumps majors separados.** Agrupar 3, 4 e 5 em `4.0.0` —
  cada bump força re-upload de todos os itens no IA (sem update parcial).
- **Não esquecer o code path legado.** `consolidate-parquet.yml` roda
  `scripts/pipeline/consolidate.py`; toda mudança de layout precisa estar lá
  *e* em `transforms.py`/`exporter.py` (hoje os schemas já são compartilhados via
  registry, mas a lógica de `ORDER BY`/serving é por-builder).
