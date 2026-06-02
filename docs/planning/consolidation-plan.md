# Plano de consolidação — do backfill ao produto

**Data:** 2026-06-02
**Contexto:** o backfill está quase completo (~157K entries no manifest). O
pipeline coleta ZIPs, arquiva no IA e faz consolidação diária em 10 tabelas
Parquet. A questão agora: como fechar a distância entre "arquivamento funcional"
e "plataforma de dados judiciais confiável".

**Princípio orientador:** *validar o schema antes de consolidar mais*, porque
cada Parquet com schema errado é retrabalho caro (re-download + re-process +
re-upload de itens no IA).

**Referência arquitetural:** padrões extraídos do projeto irmão
[ficha](https://github.com/franklinbaldo/ficha) — especificamente ADRs 0003
(schema versioning em três camadas), 0006 (validação pragmática), 0008
(Parquet-per-access-pattern), 0009 (roundtrip-equivalence como gate), e 0012
(IA como source-of-truth). Os padrões que se aplicam diretamente ao CausaGanha
são marcados com `[ficha]` nas seções abaixo.

---

## 1. Por que schema primeiro

O pipeline consolida ZIPs em 10 tabelas Parquet (`comunicacoes`, `textos`,
`destinatarios`, `partes`, `advogados`, `advogado_nomes`,
`comunicacao_advogados`, `representacoes`, `processos`, `classificacoes`).
Cada tabela é definida por um `ibis.Schema` em `transforms.py` (l.376-489).

Riscos atuais:

| Risco | Impacto |
|---|---|
| **Schema silently drifts** — DJEN API muda campos, nosso `read_json_auto` aceita qualquer coisa | Parquets no IA com colunas extras ou tipos errados; leitores DuckDB quebram |
| **Sem versão no schema** — `SCHEMA_VERSION = "3"` existe mas não é validado em leitura | Parquets v2 e v3 coexistem no IA sem como distinguir |
| **Sem validação pós-consolidação** — o pipeline grava e faz upload sem checar se o Parquet resultante respeita o schema declarado | Erro propagado em silêncio |
| **`classificacoes` é heurística v1** — keyword matching com confidence fixa 0.3, sem benchmark contínuo | Classificações de baixa qualidade congeladas no IA |
| **Manifest CSV → Parquet em migração** — decisão doc (manifest-source-of-truth.md) define o caminho mas a Fase 1 ainda não rodou | Risco de drift continua |

### Lições do ficha

O ficha enfrentou o mesmo problema com dumps da RFB (layouts mudam
silenciosamente) e resolveu com três camadas de versionamento (ADR 0003):

1. **Versão embutida no Parquet** — KV metadata no footer (`ficha.schema_version`).
2. **Manifest público** — `manifest.json` commitado, single source of truth de
   snapshots.
3. **Schemas Zod versionados e imutáveis** — `web/src/schemas/v1/`, nunca
   editados após publicação; mudanças quebram → criar `v2/`.

E com validação pragmática (ADR 0006): asserts SQL simples sobre DuckDB em vez
de Great Expectations — 5-10 regras críticas, zero deps extras, ms de execução.

O CausaGanha já tem metade das peças (Ibis schemas em Python, Zod gen via
orval). O que falta é **colá-las**: stampar a versão no Parquet, validar antes
de upload, e tornar os schemas imutáveis por versão.

---

## 2. Restrições de design

Estas restrições se aplicam a todo código no pipeline de consolidação e são
obrigatórias para qualquer novo table builder ou transform.

### 2.1 Ibis — nunca pandas

`pandas` está banido do repo (`ruff.toml` `banned-api`). Todo processamento de
dados usa **Ibis** com o backend DuckDB. Isso não é preferência de estilo — é
a garantia de que o DuckDB, não o Python, executa os joins e aggregations.

### 2.2 Transformações vetorizadas — nunca row-by-row

Proibido: `.iterrows()`, loops Python sobre DataFrames, list comprehensions que
materializam rows. Cada table builder deve ser uma expressão Ibis pura que o
DuckDB compila e executa como SQL.

**Errado:**
```python
rows = []
for record in ndjson_data:       # Python loop → O(n) overhead
    rows.append(transform(record))
```

**Certo:**
```python
t = con.read_json(path)          # DuckDB lê e transforma em SQL
result = (t.select(...).filter(...).mutate(...))  # expressão lazy
```

### 2.3 Delay de materialização — `.execute()` só no `COPY`

Expressões Ibis são **lazy** (o DuckDB só executa quando chamamos `.execute()`
ou `COPY`). Manter o plano de execução em SQL até o momento do `COPY TO` é o
que permite ao DuckDB otimizar joins multi-tabela e usar leitura por colunas.

**Regra:** chamar `.execute()` ou `.to_pyarrow()` fora do `COPY` final é sinal
de que algo pode ser reestruturado como expressão Ibis. A única exceção
permitida é `t.count().execute()` para checar se a tabela está vazia antes de
exportar.

### 2.4 UDFs Python — somente para lógica não expressável em SQL

`@ibis.udf.scalar.python` executa Python por-linha dentro do DuckDB. Usar
apenas para coisas que o SQL não tem: UUIDv5 determinístico (`djen_uuid5`),
normalização de strings com `unicodedata` (`normalize_name`). Nunca para
transformar colunas que SQL nativo expressaria em uma linha.

---

## 3. Fases de execução

### Fase 0 — Validação de schema (gate obrigatório)

**Objetivo:** garantir que nenhum Parquet é gravado/uploaded sem validar contra o
schema declarado. Impede acúmulo de dados com formato errado.

#### 0.1 Schema versioning em três camadas `[ficha ADR 0003]`

O ficha usa três camadas complementares de versionamento. Adaptamos para o
CausaGanha:

**Camada 1 — Versão embutida no Parquet (KV metadata no footer)**

Cada Parquet consolidado carrega no footer:
```
causaganha.schema_version = "3.1.0"
causaganha.item_id = "djen-2026-06-01"
causaganha.consolidated_at = "2026-06-02T07:00:00Z"
```
Lido via `parquet_kv_metadata()` do DuckDB. Custo zero, colado ao dado.

**Camada 2 — Registry em Python (ETL side)**

Criar `src/causaganha/consolidate/schema_registry.py`:

```
SchemaVersion
  version: str           # semver: "3.1.0"
  tables: dict[str, ibis.Schema]
  created_at: datetime

CURRENT_VERSION = "3.1.0"
SCHEMA_REGISTRY: dict[str, SchemaVersion] = {...}
```

- Registra cada versão do schema junto com o dict de tabelas.
- A versão atual (`CURRENT_VERSION`) é a que o pipeline usa para gravar.
- Versões anteriores ficam no registry para leitura/migração.
- **Regra do ficha:** nunca editar um schema publicado. Mudanças → nova versão.

**Camada 3 — Schemas Zod versionados no frontend**

O CausaGanha já gera Zod schemas via orval (`djen-zod.gen.ts`) para a API.
Estender para os Parquets consolidados:

```
web/src/schemas/
  v3/            ← schema atual dos 10 Parquets
    comunicacao.ts
    advogado.ts
    classificacao.ts
    ...
    index.ts     ← re-exports + VERSION = "3.1.0"
  registry.ts    ← lookup por versão (como ficha)
```

Frontend lê `causaganha.schema_version` do Parquet footer via DuckDB WASM e
seleciona o schema correto. Parquets antigos continuam legíveis.

**SemVer (adaptado do ficha ADR 0009):**
- *patch*: campo opcional novo, campo computado novo
- *minor*: campo obrigatório com default, lookup description inline
- *major*: campo removido, campo renomeado, tipo mudou

#### 0.2 Validação pós-export `[ficha ADR 0006]`

Seguindo a abordagem pragmática do ficha: asserts SQL simples sobre DuckDB, sem
framework externo (nem Great Expectations, nem Pandera no v1).

**Atenção: dois code paths de consolidação coexistem.** O workflow de produção
(`consolidate-parquet.yml`) roda `scripts/pipeline/consolidate.py` (monolito
legado), não o módulo refatorado `src/causaganha/consolidate/exporter.py`. A
validação precisa cobrir **ambos** para ser um gate real:

- **Opção A (preferida):** extrair `validate_parquet()` para um módulo
  compartilhado (`src/causaganha/consolidate/validation.py`) e importar em
  ambos os code paths — o refatorado (`exporter.py`) e o legado
  (`scripts/pipeline/consolidate.py`).
- **Opção B:** migrar o workflow para usar o módulo refatorado
  (`python -m causaganha.consolidate backfill`) antes de implementar a
  validação. Mais limpo, mas bloqueia o gate na migração do workflow.

Independente da opção, após `COPY TO` e antes do upload:

1. Abrir o Parquet com DuckDB.
2. Comparar colunas/tipos contra `TABLE_SCHEMAS[table_name]`.
3. Validar invariantes: `id` não-nulo, `tribunal` em lista conhecida,
   `data_disponibilizacao` parsável como date.
4. Se falhar: log + skip upload + não marcar checkpoint. Não falha silenciosamente.

```python
def validate_parquet(path: Path, table_name: str) -> list[str]:
    """Pragmatic validation — SQL asserts, zero extra deps."""
    errors = []
    con = duckdb.connect()
    cols = con.execute(f"DESCRIBE SELECT * FROM '{path}'").fetchall()
    expected = TABLE_SCHEMAS[table_name]
    # Column count + types match
    # NOT NULL invariants
    # Domain checks (tribunal in known list, outcome in enum)
    # Row count > 0 (WARN level)
    return errors
```

**Quando escalar:** se regras passarem de ~15, avaliar Pandera (schema-as-class)
ou dbt-style SQL tests. Não antes.

#### 0.3 Version stamp nos Parquets

Gravar `schema_version` como metadata do Parquet file (via DuckDB `KV_METADATA`):

```sql
COPY tbl TO 'x.parquet' (FORMAT PARQUET, COMPRESSION ZSTD,
  KV_METADATA {'schema_version': '3.1.0'});
```

Leitores podem checar a versão antes de consumir.

#### 0.4 Validação do NDJSON de entrada

Antes de `load_and_transform`, validar amostra do NDJSON contra os field
variants (`FIELD_*` em `djen_schema.py`). Se > 10% dos records não têm nenhum
dos campos esperados → abortar esse ZIP (DJEN mudou a API; alarme).

#### 0.5 CI gate — schema snapshot test

Novo test em `tests/test_schema_registry.py`:
- Snapshot do schema atual (colunas + tipos) serializado como JSON.
- Qualquer PR que mude `TABLE_SCHEMAS` ou `djen_schema.py` sem bumpar a versão → falha no CI.
- Protege contra drift acidental do schema.

#### 0.6 Consolidation manifest `[ficha ADR 0008]`

O ficha usa um `manifest.json` como contrato único entre ETL e frontend: lista
todos os snapshots, seus arquivos, SHA-256, row counts, e schema version. O
CausaGanha tem o `sync-manifest` (para ZIPs) mas não tem equivalente para os
Parquets consolidados.

Criar `web/public/data/consolidation-manifest.json`:

```json
{
  "schema_version": "3.1.0",
  "generated_at": "2026-06-02T07:00:00Z",
  "items": [
    {
      "item_id": "djen-2026-06-01",
      "date": "2026-06-01",
      "schema_version": "3.1.0",
      "tables": {
        "comunicacoes": { "rows": 12345, "size_bytes": 4567890, "sha256": "..." },
        "advogados":    { "rows": 890,   "size_bytes": 123456,  "sha256": "..." }
      }
    }
  ]
}
```

Benefícios:
- Frontend descobre quais Parquets existem com **um fetch** no boot.
- DuckDB WASM sabe qual schema usar antes de abrir o Parquet.
- Drift detection gratuita: diff de manifests sucessivos mostra row count drops.
- Schema version coverage visível sem varrer todos os itens no IA.

#### 0.7 Roundtrip-equivalence gate `[ficha ADR 0009]`

O ficha valida que seus Parquets denormalizados retornam os mesmos dados que o
dump cru original (`assert_roundtrip`). Adaptar para CausaGanha:

Após consolidar um date, sortear N comunicações do NDJSON bruto e verificar que
cada campo presente no Parquet bate com a extração original:

```python
def assert_roundtrip(con, ndjson_dir: Path, sample_size: int = 100) -> None:
    sample = sample_records_from_ndjson(ndjson_dir, n=sample_size)
    for rec in sample:
        parquet_row = query_comunicacao_by_id(con, rec["id"])
        assert_fields_match(rec, parquet_row, ignore=["processed_at", "texto_id"])
```

Campos computados (`texto_id`, `processed_at`, partition columns) são excluídos.
Falha → não faz upload, exatamente como no ficha.

**Entregável:** nenhum Parquet chega ao IA sem validação. Schema versionado e rastreável.

---

### Fase 1 — Manifest write-back (da decisão doc, já planejada)

Implementar a Fase 1 do `manifest-source-of-truth.md`:

1. Congelar Parquet atual como base (Fase 0 da decisão doc).
2. `render_manifest_parquet.py` faz merge dos deltas e **escreve de volta** a
   nova base Parquet (substitui o CSV como fonte canônica).
3. Corrigir as ~79K linhas `djen_raw='200'` + `djen_status='available'` →
   `djen_raw='no_publications'` + `djen_status='absent'`.

Sequência obrigatória: parar engine → rodar write-back → reiniciar engine.

**Entregável:** Parquet passa a ser a fonte autoritativa. CSV mantido como backup.

---

### Fase 2 — Consolidação confiável em escala

Com schema validado e manifest correto:

#### 2.1 Backfill da consolidação

Rodar `causaganha.consolidate backfill` sobre todas as datas com ZIPs mas sem
Parquets. O `candidates.py` já faz esse diff via `dates_needing_consolidation_from_ia`.

Prioridade: datas mais recentes primeiro (já é o default — `ORDER BY date_str DESC`).

#### 2.2 Consolidação incremental (reprocessamento zero)

Datas já consolidadas com a versão atual do schema não são reprocessadas.
Se o schema bumpar → pipeline de reconsolidação seletiva:

```
SELECT date FROM catalog
WHERE schema_version < CURRENT_VERSION
  AND has_zips = true
ORDER BY date DESC
```

#### 2.3 Monitoramento de qualidade contínuo

- **Contagem de registros por tabela por date**: dashboard widget mostrando
  `comunicacoes.count`, `advogados.count`, etc. por data. Drop repentino = alarme.
- **Distribuição de classificações**: `classificacoes.outcome` distribution por
  semana. Shift grande = keyword heuristic degradou ou API mudou.
- **Schema version coverage**: % de itens no IA com `schema_version == CURRENT`.

---

### Fase 3 — Classificação robusta (upgrade de `classificacoes`)

A tabela `classificacoes` hoje é keyword-matching v1 (confidence=0.3 fixa).
O benchmark (`data/benchmark/DESIGN.md`) já define o framework de avaliação
correto (gate + conditional, invariant winner polo, multi-model oracle).

#### 3.1 Benchmark contínuo

- `scripts/daily_benchmark_update.py` já existe. Integrá-lo ao workflow
  `consolidate-parquet.yml` para que cada run avalie o classificador contra o
  gold set.
- Threshold de deploy: só publicar classificações com accuracy >
  benchmark-target.

#### 3.2 Classificador ML

O pipeline já tem:
- `analysis/ml_document_classifier.py` — trained on embeddings
- `analysis/hybrid_analyzer.py` — keyword + RAG fusion
- `analysis/bayesian_fusion.py` — combine signals
- `scoring/openskill.py` — lawyer rating

Roadmap de upgrade:
1. Substituir `keyword_v1` por `hybrid_v2` na consolidação.
2. Gravar `metodo='hybrid_v2'` + `confidence` real (não fixa).
3. Manter `keyword_v1` como fallback para when embeddings are unavailable.

#### 3.3 Schema da `classificacoes` v2

Campos a adicionar (requires schema version bump → 4.0.0):

```
winner_polo: string         # 'A' | 'P' | 'draw' | 'unknown' (invariant winner)
recorrente_polo: string     # quem recorreu
fase_processual: string     # 'conhecimento' | 'execução' | 'recursal'
classe_processual: string
assunto_principal: string
valor_causa: float64
valor_condenacao: float64
```

Estes campos já existem em `analysis/models.py:DecisionAnalysis` mas não fluem
para o Parquet consolidado. A Fase 3 fecha esse gap.

---

### Fase 4 — Scoring e produto

Com classificações confiáveis:

#### 4.1 Lawyer ratings em escala

- `scoring/openskill.py` já implementa PlackettLuce.
- Hoje roda só para TJRO. Escalar para todos os tribunais consolidados.
- Gravar ratings como tabela Parquet adicional (`lawyer_ratings.parquet`) no IA.
- Query contract `lawyer_leaderboard.qmd` já consome; generalizar para
  multi-tribunal.

#### 4.2 Dashboard v2

Funcionalidades que dependem da consolidação confiável:

| Feature | Dependência |
|---|---|
| Busca por advogado (cross-tribunal) | `advogados` + `advogado_nomes` consolidados |
| Explorador de publicações (DuckDB WASM) | Parquets versionados no IA |
| Página de advogado com rating + histórico | `lawyer_ratings` + `comunicacao_advogados` |
| Heatmap de classificações por tribunal | `classificacoes` v2 |
| Comparador de tribunais por outcome | `classificacoes` v2 + `comunicacoes` |

#### 4.3 API de dados abertos `[ficha ADR 0004, 0012]`

- Manter Parquets no IA como API primária (HTTP Range + DuckDB httpfs).
- `catalog.duckdb` com views remotas já existe.
- Documentar o schema versionado como contrato público estável.
- **IA como source-of-truth** (padrão ficha ADR 0012): os Parquets no IA são
  o artefato canônico. O dashboard é uma view. Se o repo sumir, os dados
  continuam acessíveis no IA.

#### 4.4 IA practicality probe `[ficha ia_practicality.py]`

Script de diagnóstico que exercita os Parquets consolidados no IA end-to-end:

1. Descobre itens `djen-*` no IA.
2. Para cada Parquet: `DESCRIBE` (schema inference), `COUNT(*)` (row group
   stats), `LIMIT 5` (real data access).
3. Compara colunas contra `MINIMAL_REQUIRED_COLUMNS` por tabela.
4. Hard failures (zero rows, missing required columns) → exit non-zero.
5. Soft warnings (optional column missing, schema drift) → annotations.

Roda como CI job periódico (weekly) e detecta degradação de dados no IA antes
que usuários reportem.

---

## 4. Schema de validação — especificação detalhada

### 4.1 Invariantes por tabela

| Tabela | Invariante | Severidade |
|---|---|---|
| `comunicacoes` | `id` NOT NULL, `tribunal` in KNOWN_TRIBUNALS, `data_disponibilizacao` IS DATE | BLOCK |
| `comunicacoes` | `texto_id` NOT NULL when `texto` exists in raw | WARN |
| `textos` | `id` NOT NULL, `texto` NOT EMPTY | BLOCK |
| `destinatarios` | `comunicacao_id` FK → `comunicacoes.id` | WARN |
| `advogados` | `id` NOT NULL, at least one of `numero_oab`/`nome` non-empty | BLOCK |
| `classificacoes` | `outcome` in {'WIN','LOSS','PARTIAL','SETTLEMENT','UNKNOWN'} | BLOCK |
| `classificacoes` | `confidence` BETWEEN 0 AND 1 | BLOCK |
| `processos` | `numero_processo` matches `\d{20}` or masked format | WARN |
| All tables | zero rows → WARN (empty date is possible but suspicious) | WARN |
| All tables | column count matches schema | BLOCK |
| All tables | column types match schema | BLOCK |

BLOCK = não faz upload, não marca checkpoint.
WARN = log + upload procede, mas incrementa contador de warnings.

### 4.2 Validação cruzada entre tabelas

Anti-join containment checks (not just cardinality — `COUNT <=` would miss
orphaned IDs where child has IDs absent from parent):

```sql
SELECT comunicacao_id FROM destinatarios
WHERE comunicacao_id NOT IN (SELECT id FROM comunicacoes)

SELECT advogado_id FROM comunicacao_advogados
WHERE advogado_id NOT IN (SELECT id FROM advogados)

SELECT texto_id FROM classificacoes
WHERE texto_id NOT IN (SELECT id FROM textos)
```

Any rows returned = WARN (possible FK to comunicação from another item/date).

### 4.3 Formato do campo `djen_raw` (manifest)

Valores válidos pós-Fase 1:

```
'200'              # HTTP 200 com URL (available)
'no_publications'  # HTTP 200 sem URL ("Sem comunicações")
'404'              # Not Found (genuinely absent)
'400'              # Bad Request (holidays)
'403'              # Forbidden (rate limit → unknown)
'500'              # Internal Server Error (transient → unknown)
'502'              # Bad Gateway (transient → unknown)
'503'              # Service Unavailable (transient → unknown)
'504'              # Gateway Timeout (transient → unknown)
'timeout'          # Request timeout (unknown)
'network'          # Network error (unknown)
```

Must match `TRANSIENT_CODES` in `src/djen_backup/manifest.py` — the 5xx codes
are legitimate server failures that the engine records and retries. Validation
on write-back and checker.

---

## 5. Ordem de implementação e estimativas

| # | Tarefa | Fase | Bloqueia | Estimativa |
|---|---|---|---|---|
| 1 | Schema registry 3 camadas (Python + KV metadata + Zod) | 0.1, 0.3 | Tudo | M |
| 2 | Validação pós-export em `exporter.py` | 0.2 | Upload de novos Parquets | P |
| 3 | CI snapshot test do schema | 0.5 | PRs que tocam schema | P |
| 4 | Validação NDJSON de entrada | 0.4 | — | M |
| 5 | Consolidation manifest JSON | 0.6 | Dashboard v2 | M |
| 6 | Roundtrip-equivalence gate | 0.7 | — | M |
| 7 | Manifest write-back (Fase 1 da decisão doc) | 1 | Consolidação correta | M |
| 8 | Backfill da consolidação em escala | 2.1 | — | G |
| 9 | Monitoramento de qualidade | 2.3 | — | M |
| 10 | Benchmark contínuo | 3.1 | Upgrade do classificador | M |
| 11 | Classificador hybrid_v2 | 3.2 | — | G |
| 12 | Schema classificacoes v2 | 3.3 | Precisa de 1 | M |
| 13 | Lawyer ratings multi-tribunal | 4.1 | Precisa de 11 | M |
| 14 | Dashboard v2 features | 4.2 | Precisa de 8, 12 | G |
| 15 | IA practicality probe (CI weekly) | 4.4 | — | M |

P = pequeno (< 1 dia), M = médio (1-3 dias), G = grande (> 3 dias).

**Caminho crítico:** 1 → 2 → 7 → 8 → 11 → 12 → 13 → 14

**Quick wins imediatos (Fase 0):** tarefas 1, 2, 3 podem ser feitas hoje e já
protegem contra retrabalho.

---

## 6. O que NÃO fazer

- **Não reconsolidar sem schema validation.** Cada Parquet errado no IA é um
  item que precisa ser re-uploaded (IA não suporta update parcial).
- **Não mudar o schema sem version bump.** Consumidores (DuckDB WASM no
  dashboard) dependem da estabilidade das colunas.
- **Não editar um schema publicado `[ficha]`.** Mudanças quebram → criar nova
  versão. Schemas antigos ficam imutáveis no registry para sempre.
- **Não confiar no CSV como fonte.** Decisão já tomada: o Parquet é mais correto.
  O CSV é backup histórico.
- **Não deploiar classificador novo sem benchmark.** O gold set existe e o
  framework de avaliação está definido. Usá-lo.
- **Não adicionar campos ao Parquet consolidado sem atualizar `TABLE_SCHEMAS`.**
  DuckDB `union_by_name` resolve leitura, mas schemas implícitos viram dívida.
- **Não adotar Great Expectations / framework pesado para <15 regras `[ficha]`.**
  Asserts SQL sobre DuckDB. Zero deps extras. Reconsiderar Pandera se regras
  passarem de ~15-20.
- **Não separar metadado do dado `[ficha]`.** Schema version vive no footer do
  Parquet (KV metadata), não em arquivo lateral. Fragiliza se separar.
