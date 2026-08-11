# RFC 0004 — Embeddings dos acórdãos do TJRO JURIS e STJ

- **Status:** Proposto
- **Data:** 2026-06-26
- **Depende de:** RFC 0003 (ingestão TJRO JURIS), RFC 0002 (ingestão STJ)
- **Escopo:** Geração, armazenamento e arquivamento de embeddings vetoriais para
  cada acórdão ingerido do TJRO JURIS e do STJ, reutilizando a infraestrutura
  existente em `src/causaganha/analysis/`.

## 1. Resumo executivo

O projeto já possui uma pilha de embeddings madura (Jina v4, DuckDB, Parquet,
LanceDB) usada para análise de decisões do DJEN. Este RFC estende essa pilha
para cobrir os dois novos corpora:

- **TJRO JURIS**: acórdãos, sentenças, votos e ementas do sistema JURIS
  (ingeridos via RFC 0003).
- **STJ Primeira Seção**: espelhos de acórdãos com tese jurídica, ementa e
  dispositivo (ingeridos via RFC 0002).

O objetivo é habilitar busca semântica, agrupamento de teses e cruzamento
entre corpora sem mudança na arquitetura existente — apenas novos adaptadores
de fonte e novos jobs de embedding.

## 2. Motivação

| Caso de uso | Corpus |
|---|---|
| "Quais acórdãos do TJRO tratam de usucapião extrajudicial?" | JURIS |
| "Encontre decisões do TJRO similares a esta tese do STJ" | JURIS + STJ |
| "Agrupe os temas repetitivos do STJ por proximidade semântica" | STJ |
| "Qual o acórdão do TJRO mais próximo do tema 1110 do STJ?" | JURIS + STJ |
| Alimentar o classificador ML com exemplos rotulados por similaridade | JURIS |

Sem embeddings, esses casos exigem busca por palavra-chave — frágil para
linguagem jurídica onde sinônimos e paráfrases são ubíquos.

## 3. Infraestrutura existente reutilizada

| Componente | Caminho | Papel |
|---|---|---|
| `EmbeddingService` | `src/causaganha/analysis/embedding_service.py` | Gera embeddings com chunking e retry |
| `EmbeddingStorage` | `src/causaganha/storage/embedding_storage.py` | Persiste em DuckDB, exporta Parquet |
| `embedding_models.py` | `src/causaganha/analysis/embedding_models.py` | Configuração de modelo (Jina v4, 1024D) |
| `api_embedder.py` | `src/causaganha/analysis/api_embedder.py` | Cliente Jina AI com rate limit e budget |
| `export_daily_embeddings.py` | `scripts/export_daily_embeddings.py` | Exporta Parquet para o IA |
| `embedding_job.py` | `scripts/embedding_job.py` | Worker de embedding contínuo |

Não há necessidade de criar nova infraestrutura de vetores. O que muda é
**de onde vêm os textos** e **como os metadados de fonte são registrados**.

## 4. Campos a embedar

### 4.1 TJRO JURIS

Campo principal: **`texto_limpo`** (inteiro teor limpo de HTML, gerado pela
RFC 0003).

Estratégia de chunking: `auto` com max_tokens do modelo (32K para Jina v4).
Decisões longas (acórdãos de 2º grau) serão divididas em chunks; ementas e
decisões singulares cabem em chunk único.

Prefixo contextual:
```
Acórdão do TJRO ({classe_judicial}, {orgao}, {data_julgamento}):
```

### 4.2 STJ Primeira Seção

Campo principal: concatenação de **`ementa` + `teseJuridica`** (os campos mais
densos semanticamente; `decisao` e `informacoesComplementares` são opcionais
numa segunda fase).

Estratégia de chunking: `auto`; a maioria dos espelhos cabe em chunk único
(ementa + tese raramente ultrapassa 2K tokens).

Prefixo contextual:
```
Espelho de acórdão do STJ ({siglaClasse}, tema {tema}, relator {ministroRelator}):
```

## 5. Identificação e deduplicação

O `texto_id` existente é UUID v5 derivado do conteúdo textual. Para DJEN isso
é suficiente, mas para JURIS/STJ introduz um problema: decisões de tema
repetitivo frequentemente compartilham texto idêntico ou quase idêntico. Como
`EmbeddingStorage.insert_embeddings()` deleta todas as linhas com o mesmo
`texto_id` antes de inserir, dois documentos distintos com texto igual teriam o
mesmo `texto_id` — o segundo sobrescreveria silenciosamente o primeiro,
perdendo metadados de fonte.

**Solução**: usar um `doc_id` composto de `(fonte, id_documento)` como
identificador primário do embedding, separando identidade de conteúdo de
identidade de documento:

```python
# doc_id: identidade do documento (fonte + id único da fonte)
doc_id = uuid5(NAMESPACE, f"{fonte}:{id_documento}")

# content_hash: UUID v5 do texto (para dedup de conteúdo dentro da mesma fonte)
content_hash = uuid5(NAMESPACE, texto)
```

A chave primária da tabela passa a ser `(doc_id, chunk_index)`. O campo
`content_hash` fica como coluna auxiliar para detectar documentos com texto
idêntico sem suprimi-los.

Campos de metadados adicionais a persistir junto ao embedding:

| Campo | JURIS | STJ |
|---|---|---|
| `fonte` | `"tjro_juris"` | `"stj_primeira_secao"` |
| `id_documento` | `id_processo_documento` | `id` |
| `nr_processo` | CNJ formatado | `numeroProcesso` |
| `tipo` | `tipo` (ACÓRDÃO, SENTENÇA…) | `siglaClasse` |
| `data_julgamento` | `data_julgamento` | `dataDecisao` |
| `orgao` | `orgao` | `nomeOrgaoJulgador` |
| `relator` | `relator` | `ministroRelator` |
| `tema_stj` | — | `tema` (número do tema repetitivo) |

Esses metadados são armazenados na tabela DuckDB ao lado do vetor para
permitir filtros eficientes na busca.

> **Limitação atual do `EmbeddingStorage`**: a tabela existente armazena
> apenas `texto_id`, `chunk_index`, vetor, campos de versão, `text_preview` e
> `created_at`. Ela **não possui** colunas para `fonte`, `id_documento`,
> `tipo`, `data_julgamento`, `orgao`, `relator` ou `tema_stj`. A implementação
> desta RFC requer uma **migração de schema** em `EmbeddingStorage` para
> adicionar essas colunas (nullable para compatibilidade com embeddings DJEN
> existentes) e um método `insert_with_metadata()` que persista o vetor e os
> metadados de fonte na mesma transação. Sem essa alteração, as queries de
> similaridade filtradas por `fonte` ou os cruzamentos entre corpora não
> funcionam.

## 6. Armazenamento

### 6.1 DuckDB local

Tabela: `embeddings_jina_jina__v4_1024` — nome resolvido por
`EmbeddingStorage._get_table_name("jina-embeddings-v4", 1024)` (mesma usada
pelo DJEN).

**Migração de schema necessária**: adicionar colunas de metadados à tabela
existente via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`:

```sql
ALTER TABLE embeddings_jina_jina__v4_1024
  ADD COLUMN IF NOT EXISTS fonte         VARCHAR,
  ADD COLUMN IF NOT EXISTS id_documento  VARCHAR,
  ADD COLUMN IF NOT EXISTS nr_processo   VARCHAR,
  ADD COLUMN IF NOT EXISTS tipo          VARCHAR,
  ADD COLUMN IF NOT EXISTS data_julgamento DATE,
  ADD COLUMN IF NOT EXISTS orgao         VARCHAR,
  ADD COLUMN IF NOT EXISTS relator       VARCHAR,
  ADD COLUMN IF NOT EXISTS tema_stj      VARCHAR;
```

As colunas são nullable — os embeddings DJEN existentes ficam com `NULL` nelas
sem quebrar consultas de similaridade não filtradas.

A coluna `fonte` distingue a origem. Queries de similaridade podem filtrar
por `fonte` ou cruzar os três corpora.

### 6.2 Parquet no Internet Archive

Exportar embeddings para o IA junto com os dados brutos:

| Item IA | Arquivo de embedding |
|---|---|
| `tjro-juris-AAAA` | `tjro-juris-AAAA-embeddings.parquet` |
| `stj-acordaos-primeira-secao` | `stj-embeddings-YYYYMMDD.parquet` |

Schema do Parquet:

```
texto_id          : string   (UUID v5)
fonte             : string   ("tjro_juris" | "stj_primeira_secao")
id_documento      : string
nr_processo       : string
chunk_index       : int32
embedding         : list<float32>[1024]
model_id          : string   ("jina-embeddings-v4")
model_dim         : int32    (1024)
created_at        : timestamp
```

### 6.3 LanceDB (opcional)

Criar tabelas `tjro_juris` e `stj_primeira_secao` no LanceDB existente
(`data/lancedb/`) para busca vetorial de baixa latência no dashboard.

## 7. Jobs e CLI

### 7.1 Novos adaptadores de fonte

```python
# src/causaganha/analysis/sources/tjro_juris_source.py
class TJROJurisSource:
    """Itera sobre os Parquets do TJRO JURIS e produz (texto, metadados)."""


# src/causaganha/analysis/sources/stj_source.py
class STJSource:
    """Itera sobre o Parquet consolidado do STJ e produz (texto, metadados)."""
```

Ambos implementam uma interface `TextSource` a ser definida em
`src/causaganha/analysis/sources/__init__.py`:

```python
class TextSource(Protocol):
    def iter_texts(self) -> Iterator[tuple[str, dict]]:
        """Yield (text, metadata) pairs to embed."""
```

**Modificação necessária em `embedding_job.py`**: o job atual consulta
exclusivamente a tabela `intimations` e usa `load_decision_text` para buscar
o texto — ele **não** descobre automaticamente novas fontes. A implementação
desta RFC requer alterar `embedding_job.py` (ou criar um novo job
`embed_sources_job.py`) para:

1. Aceitar uma lista de `TextSource` configurável.
2. Para cada fonte, iterar `iter_texts()`, gerar embeddings via `EmbeddingService`
   e persistir via `EmbeddingStorage` com os metadados de fonte.

### 7.2 CLI

```bash
# Embedar TJRO JURIS (todos os anos disponíveis)
uv run causaganha embed tjro-juris [--ano AAAA] [--force]

# Embedar STJ
uv run causaganha embed stj [--force]

# Exportar embeddings para Parquet + upload IA
uv run causaganha embed export --fonte tjro-juris
uv run causaganha embed export --fonte stj
```

### 7.3 Integração com jobs existentes

`continuous_embedding_service.py` pode receber as novas fontes via
configuração, **mas apenas após a modificação em `embedding_job.py`** descrita
em § 7.1. O registro das fontes (`TJROJurisSource`, `STJSource`) na lista do
serviço é o passo final, não o único necessário.

## 8. Estimativa de volume e custo

### 8.1 TJRO JURIS

- Acervo estimado: ~100k documentos
- Tamanho médio do texto limpo: ~3K tokens (acórdãos de 2º grau são maiores)
- Chunks estimados: ~120k (maioria 1 chunk/doc, alguns 2–3)
- Tokens totais: ~360M tokens
- Custo Jina AI (10M grátis/mês + R$ 0,02/M tokens adicionais): ~R$ 7,00 pelo acervo completo

### 8.2 STJ Primeira Seção

- Registros estimados: ~50k acórdãos (acervo histórico)
- Tamanho médio ementa + tese: ~800 tokens
- Tokens totais: ~40M tokens — dentro da cota gratuita mensal do Jina

### 8.3 Incremental (pós-backfill)

Novos documentos mensais: ~500 TJRO + ~200 STJ → negligível.

## 9. Decisões de design

### 9.1 Mesma tabela DuckDB, coluna `fonte` como discriminador

Alternativa seria tabelas separadas por fonte. A coluna `fonte` é mais simples
e permite queries de similaridade cruzada sem JOIN — mais útil para o caso
"acórdão TJRO mais próximo do tema STJ".

### 9.2 Embedar `ementa + teseJuridica` para o STJ, não o inteiro teor

O inteiro teor completo não está no dataset de espelhos (apenas referência de
publicação). `ementa + teseJuridica` são os campos mais ricos semanticamente
e suficientes para busca e agrupamento de teses.

### 9.3 Mesmo modelo (Jina v4) para os três corpora

Garante que os vetores são comparáveis entre DJEN, JURIS e STJ. Trocar o
modelo invalidaria comparações cruzadas — manter consistência é mais valioso
que otimizar por corpus.

### 9.4 Não indexar `termosAuxiliares` ou `referenciasLegislativas` do STJ

Esses campos são listas estruturadas, não texto corrido. Embedá-los
separadamente seria um caso de uso específico (busca por norma). Fora do
escopo desta RFC.

## 10. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Cota Jina AI esgotada antes do backfill completo | Token budget tracker existente; fallback para `perplexity/pplx-embed-v1-0.6b` local |
| Texto limpo do JURIS vazio para algum documento | Pular e logar; `texto_id` baseado em conteúdo garante que retry futuro reprocessa |
| Mudança de modelo quebra comparabilidade | Coluna `model_id` no Parquet; nunca misturar vetores de modelos diferentes na mesma busca |
| Parquet de embeddings grande demais para o IA | Comprimir com ZSTD nível 9 (já feito em `export_daily_embeddings.py`); particionar por ano |
| Reprocessamento duplica vetores | UUID v5 content-addressable já previne duplicação no storage existente |

## 11. Fora de escopo

- Busca semântica no dashboard (requer endpoint de busca, tratado separadamente).
- Fine-tuning de modelo para domínio jurídico brasileiro.
- Embeddings do campo `decisao` completo do STJ (texto longo, baixa relação
  sinal/ruído para busca semântica).
- Embeddings de documentos de 1º grau do JURIS (sentença/decisão singular) —
  podem ser adicionados na mesma arquitetura sem mudança.

## 12. Critérios de aceitação

- [ ] `TJROJurisSource` e `STJSource` implementam a interface de fontes.
- [ ] `uv run causaganha embed tjro-juris` processa o acervo completo sem erro.
- [ ] `uv run causaganha embed stj` processa o acervo completo sem erro.
- [ ] Nenhum `texto_id` duplicado na tabela DuckDB após reprocessamento.
- [ ] Parquets de embeddings exportados e enviados para os itens IA corretos.
- [ ] Query de similaridade cruzada (`fonte IN ('tjro_juris', 'stj_primeira_secao')`) retorna resultados sensatos em teste manual.
- [ ] `uv run ruff check` e `uv run pytest -q` passam.

## 13. Referências

- Infraestrutura existente: `src/causaganha/analysis/embedding_service.py`
- Storage: `src/causaganha/storage/embedding_storage.py`
- Export job: `scripts/export_daily_embeddings.py`
- RFC 0002: `docs/rfc/0002-stj-acordaos-dataset.md`
- RFC 0003: `docs/rfc/0003-tjro-juris-scraping.md`
- Modelo: Jina v4 (`jina-embeddings-v4`, 1024D, 32K tokens)
