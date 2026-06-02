# Plano de consolidação — do backfill ao produto

**Data:** 2026-06-02
**Contexto:** o backfill está quase completo (~157K entries no manifest). O
pipeline coleta ZIPs, arquiva no IA e faz consolidação diária em 10 tabelas
Parquet. A questão agora: como fechar a distância entre "arquivamento funcional"
e "plataforma de dados judiciais confiável".

**Princípio orientador:** *validar o schema antes de consolidar mais*, porque
cada Parquet com schema errado é retrabalho caro (re-download + re-process +
re-upload de itens no IA).

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

---

## 2. Fases de execução

### Fase 0 — Validação de schema (gate obrigatório)

**Objetivo:** garantir que nenhum Parquet é gravado/uploaded sem validar contra o
schema declarado. Impede acúmulo de dados com formato errado.

#### 0.1 Schema registry em Python

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

#### 0.2 Validação pós-export

Em `exporter.py`, após `COPY TO`, antes do upload:

1. Abrir o Parquet com DuckDB.
2. Comparar colunas/tipos contra `TABLE_SCHEMAS[table_name]`.
3. Validar invariantes: `id` não-nulo, `tribunal` em lista conhecida,
   `data_disponibilizacao` parsável como date.
4. Se falhar: log + skip upload + não marcar checkpoint. Não falha silenciosamente.

#### 0.3 Version stamp nos Parquets

Gravar `schema_version` como metadata do Parquet file (via DuckDB `KV_METADATA`):

```sql
COPY tbl TO 'x.parquet' (FORMAT PARQUET, COMPRESSION ZSTD,
  KV_METADATA {schema_version: '3.1.0'});
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

#### 4.3 API de dados abertos

- Manter Parquets no IA como API primária (HTTP Range + DuckDB httpfs).
- `catalog.duckdb` com views remotas já existe.
- Documentar o schema versionado como contrato público estável.

---

## 3. Schema de validação — especificação detalhada

### 3.1 Invariantes por tabela

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

### 3.2 Validação cruzada entre tabelas

```
COUNT(DISTINCT comunicacao_id FROM destinatarios)
  <= COUNT(DISTINCT id FROM comunicacoes)

COUNT(DISTINCT advogado_id FROM comunicacao_advogados)
  <= COUNT(DISTINCT id FROM advogados)

COUNT(DISTINCT texto_id FROM classificacoes)
  <= COUNT(DISTINCT id FROM textos)
```

Violação = WARN (possível referência a comunicação de outro item/date).

### 3.3 Formato do campo `djen_raw` (manifest)

Valores válidos pós-Fase 1:

```
'200'              # HTTP 200 com URL (available)
'no_publications'  # HTTP 200 sem URL ("Sem comunicações")
'404'              # Not Found (genuinely absent)
'400'              # Bad Request (holidays)
'403'              # Forbidden (rate limit → unknown)
'timeout'          # Request timeout (unknown)
'network'          # Network error (unknown)
```

Qualquer outro valor é inválido. Validação no write-back e no checker.

---

## 4. Ordem de implementação e estimativas

| # | Tarefa | Fase | Bloqueia | Estimativa |
|---|---|---|---|---|
| 1 | Schema registry + version stamp | 0.1, 0.3 | Tudo | P |
| 2 | Validação pós-export em `exporter.py` | 0.2 | Upload de novos Parquets | P |
| 3 | CI snapshot test do schema | 0.5 | PRs que tocam schema | P |
| 4 | Validação NDJSON de entrada | 0.4 | — | M |
| 5 | Manifest write-back (Fase 1 da decisão doc) | 1 | Consolidação correta | M |
| 6 | Backfill da consolidação em escala | 2.1 | — | G |
| 7 | Monitoramento de qualidade | 2.3 | — | M |
| 8 | Benchmark contínuo | 3.1 | Upgrade do classificador | M |
| 9 | Classificador hybrid_v2 | 3.2 | — | G |
| 10 | Schema classificacoes v2 | 3.3 | Precisa de 1 | M |
| 11 | Lawyer ratings multi-tribunal | 4.1 | Precisa de 9 | M |
| 12 | Dashboard v2 features | 4.2 | Precisa de 6, 10 | G |

P = pequeno (< 1 dia), M = médio (1-3 dias), G = grande (> 3 dias).

**Caminho crítico:** 1 → 2 → 5 → 6 → 9 → 10 → 11 → 12

**Quick wins imediatos (Fase 0):** tarefas 1, 2, 3 podem ser feitas hoje e já
protegem contra retrabalho.

---

## 5. O que NÃO fazer

- **Não reconsolidar sem schema validation.** Cada Parquet errado no IA é um
  item que precisa ser re-uploaded (IA não suporta update parcial).
- **Não mudar o schema sem version bump.** Consumidores (DuckDB WASM no
  dashboard) dependem da estabilidade das colunas.
- **Não confiar no CSV como fonte.** Decisão já tomada: o Parquet é mais correto.
  O CSV é backup histórico.
- **Não deploiar classificador novo sem benchmark.** O gold set existe e o
  framework de avaliação está definido. Usá-lo.
- **Não adicionar campos ao Parquet consolidado sem atualizar `TABLE_SCHEMAS`.**
  DuckDB `union_by_name` resolve leitura, mas schemas implícitos viram dívida.
