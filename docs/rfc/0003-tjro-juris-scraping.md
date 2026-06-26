# RFC 0003 — Coleta e arquivamento da jurisprudência do TJRO (sistema JURIS)

- **Status:** Proposto
- **Data:** 2026-06-26
- **Relacionado:** RFC 0002 (espelhos STJ), CLAUDE.md (arquitetura djen-backup)
- **Escopo:** Ingestão contínua dos documentos jurisprudenciais do TJRO via a
  API do sistema JURIS, arquivamento no Internet Archive e exposição no
  dashboard.

## 1. Resumo executivo

O TJRO publica sua jurisprudência pelo sistema JURIS
(`juris-back.tjro.jus.br`, indexado em Elasticsearch). O acervo cobre
acórdãos, sentenças, votos, ementas, decisões e relatórios de 1º e 2º graus.
O portal é aberto e não requer autenticação.

Este RFC propõe:

1. Um **módulo de coleta** (`src/tjro_juris/`) que consume a API real do JURIS
   via `POST /search/varios_parametros/`, pagina o acervo completo, limpa o
   HTML do inteiro teor e serializa os documentos em Parquet.
2. **Arquivamento incremental** no Internet Archive sob itens particionados por
   ano (`tjro-juris-AAAA`).
3. Três **query contracts** (`.qmd`) para o dashboard: totais, distribuição por
   tipo/classe e ranking de órgãos julgadores.
4. Uma **skill Claude Code** (`.claude/skills/juris-tjro/`) que permite
   consultar o JURIS interativamente durante sessões de desenvolvimento.

## 2. Motivação

O pipeline DJEN captura os **cadernos diários** do TJRO (quando e o que foi
publicado). A jurisprudência do JURIS adiciona o **conteúdo estruturado** das
decisões: inteiro teor, ementa, relator, órgão, classe processual e número CNJ
definitivo. Cruzar as duas fontes permite:

- Confirmar se uma decisão publicada no DJEN chegou ao acervo de jurisprudência.
- Calcular o lag médio entre julgamento e publicação no DJEN.
- Servir busca por relator, órgão, classe e tema no dashboard do TJRO.
- Alimentar pipelines de análise (segmentador de decisões, classificador ML)
  com decisões reais rotuladas por tipo e classe.

## 3. Fonte de dados

| Propriedade | Valor |
|---|---|
| Endpoint de busca | `POST https://juris-back.tjro.jus.br/search/varios_parametros/` |
| Endpoint de agregações | `GET https://juris-back.tjro.jus.br/search/agregacoes` |
| Portal de consulta | `https://juris.tjro.jus.br/jurisprudencia/` |
| Autenticação | Nenhuma (campo `token: ""` no corpo) |
| Tecnologia backend | Django REST Framework + Elasticsearch |
| Tamanho do acervo | ~100k+ documentos (estimativa via facetas) |
| Frequência de atualização | Contínua (novos documentos a cada sessão de julgamento) |

### 3.1 Tipos de documento disponíveis

`ACÓRDÃO`, `DECISÃO`, `DECISÃO DA PRESIDÊNCIA`, `SENTENÇA`, `VOTO`,
`EMENTA`, `RELATÓRIO`.

### 3.2 Campos relevantes por documento

| Campo | Descrição |
|---|---|
| `nr_processo` | Número CNJ (20 dígitos sem máscara) |
| `tipo` | Tipo do documento (ver 3.1) |
| `ds_classe_judicial` | Classe processual (ex: "APELAÇÃO CÍVEL") |
| `ds_orgao_julgador` / `ds_orgao_julgador_colegiado` | Órgão julgador |
| `nome_relator_acordao` / `ds_nome` | Relator (2º grau) ou magistrado (1º grau) |
| `dtjulgamento` | Data do julgamento (ISO) |
| `dtjulgamento_str` | Data formatada |
| `sistema_origem` | `PJEPG` (1º grau) ou `PJESG` (2º grau) |
| `ds_modelo_documento` | Inteiro teor em HTML (contém imagens base64 embutidas — remover antes de persistir) |
| `id_processo_documento` | ID único do documento (chave primária para dedup) |
| `id_documento_principal` | Referência ao documento principal do processo |

### 3.3 Armadilhas conhecidas da API

Documentadas em detalhe na skill (`.claude/skills/juris-tjro/SKILL.md`):

- **Busca textual é OR**: mais palavras = mais resultados, não menos. Filtros
  AND devem ser aplicados client-side sobre o inteiro teor.
- **`tipo` deve ser array**: string crua no campo `tipo` derruba o servidor
  (HTTP 500).
- **Filtro de data por range quebra no servidor**: `gte/lte` → 500; aplicar
  client-side.
- **`GET /search/documentos/`** ignora parâmetros e retorna o corpus inteiro —
  não usar para busca filtrada.
- **Inteiro teor vem como HTML com imagens base64** (~dezenas de KB por
  documento): limpar antes de persistir.
- Paginação via campos `from`/`size` no corpo do POST; máximo 400 por chamada.

## 4. Proposta técnica

### 4.1 Estrutura de diretórios

```
src/tjro_juris/
├── __init__.py
├── __main__.py        — CLI (Typer): crawl, upload, status
├── client.py          — wrapper da API JURIS (buscar_raw, clean_html, etc.)
├── crawler.py         — paginação do acervo completo por tipo + janela de data
├── manifest.py        — ManifestJuris: (tipo, mes_ano) → ia_status, n_docs
├── dedup.py           — deduplicação por id_processo_documento via DuckDB
└── archive.py         — upload IA (reutiliza padrões de djen_backup/archive.py)

.claude/skills/juris-tjro/
├── SKILL.md           — skill de consulta interativa para sessões Claude Code
└── scripts/
    └── juris.py       — cliente CLI stdlib-only (buscar, processo, texto, facetas)

web/src/queries/
├── juris_totals.qmd           — total de documentos por tipo
├── juris_classes.qmd          — distribuição por classe judicial
└── juris_orgaos.qmd           — ranking de órgãos julgadores
```

### 4.2 Manifest do TJRO JURIS

Arquivo separado: `tjro-juris-manifest.csv`.

| Coluna | Descrição |
|---|---|
| `tipo` | Tipo de documento (`ACÓRDÃO`, `SENTENÇA`, etc.) |
| `mes_ano` | Janela de extração (`AAAA-MM`) |
| `ia_status` | `""` \| `"uploaded"` |
| `n_docs` | Quantidade de documentos nessa janela |
| `updated_at` | Timestamp da última atualização |

### 4.3 Estratégia de paginação

O endpoint limita `size` a 400 por chamada. Para varrer o acervo completo sem
depender de scroll/cursor (o Elasticsearch do JURIS não expõe `search_after`):

1. **Particionar por tipo × mês de julgamento**: cada célula `(tipo, AAAA-MM)`
   é uma unidade de coleta. **Importante**: o servidor não suporta filtro de
   data via `gte/lte` (retorna HTTP 500). O mês é apenas um rótulo de janela
   para o manifest — a coleta faz GET sem filtro de data e o filtro
   `AAAA-MM` é aplicado **client-side** sobre `dtjulgamento` retornado nos
   resultados.
2. Para células com mais de 400 documentos: repartir por `ds_classe_judicial`
   usando os buckets do endpoint de agregações. Se ainda assim superar 400,
   paginar por `from`/`size` iterativamente até a resposta retornar menos
   que `size` resultados (condição de parada).
3. Deduplicar por `id_processo_documento` antes de persistir — um documento
   pode aparecer em mais de uma janela se a atribuição client-side for
   imprecisa.

### 4.4 Limpeza do inteiro teor

Antes de qualquer persistência, aplicar `clean_html()` (já implementada em
`scripts/juris.py`):
- Remove `<img>` com base64 embutido.
- Remove `<style>` e `<script>`.
- Remove demais tags HTML.
- Decodifica entidades HTML.
- Normaliza espaços.

O campo `ds_modelo_documento` **não** é armazenado no Parquet bruto — apenas o
texto limpo (`texto_limpo`) para evitar explosão de tamanho.

### 4.5 Nomenclatura no Internet Archive

- **Itens**: `tjro-juris-AAAA` (um por ano de julgamento)
- **Arquivos**: `tjro-juris-AAAA-MM-{TIPO}.parquet`
- **Snapshot consolidado**: `tjro-juris-AAAA-dedup.parquet` (um por ano,
  substituído a cada ciclo)

### 4.6 Schema Parquet

```
id_documento        : int64   (= id_processo_documento, chave primária)
nr_processo         : string  (20 dígitos, sem máscara)
tipo                : string
classe_judicial     : string
orgao               : string
relator             : string
sistema_origem      : string  (PJEPG | PJESG)
data_julgamento     : date32
texto_limpo         : string  (inteiro teor limpo)
url_portal          : string
extraido_em         : timestamp
```

### 4.7 Integração com o dashboard

Três query contracts leem o snapshot consolidado via DuckDB:

- **`juris_totals.qmd`**: total de documentos por tipo e por ano.
- **`juris_classes.qmd`**: top-30 classes judiciais por volume.
- **`juris_orgaos.qmd`**: ranking de órgãos julgadores (colegiados e singulares
  separados).

### 4.8 Skill Claude Code

A skill em `.claude/skills/juris-tjro/` (já inclusa neste commit) usa stdlib
Python puro e pode ser invocada em qualquer sessão Claude Code sem instalar
dependências:

```
python .claude/skills/juris-tjro/scripts/juris.py buscar "usucapião" --tipo ACÓRDÃO
python .claude/skills/juris-tjro/scripts/juris.py processo 7030969-47.2024.8.22.0001
python .claude/skills/juris-tjro/scripts/juris.py texto 21458095
python .claude/skills/juris-tjro/scripts/juris.py facetas "alimentos"
```

## 5. Decisões de design

### 5.1 Partição por tipo × mês vs. cursor global

O JURIS não expõe scroll/cursor e o limite de 400 por página impede varrer
janelas grandes de uma vez. A partição tipo × mês mantém cada célula abaixo do
limite na maioria dos casos; as exceções são tratadas por sub-partição por
classe (§ 4.3).

### 5.2 Texto limpo no Parquet, HTML descartado

O HTML bruto contém imagens base64 que inflam cada documento em dezenas de KB.
Para o acervo completo isso inviabiliza o armazenamento. O texto limpo é
suficiente para busca full-text, treinamento de modelos e exibição no dashboard.

### 5.3 Items IA particionados por ano

Análogo ao padrão `djen-{tribunal}-{year}`. Itens anuais mantêm o tamanho
gerenciável e facilitam consultas históricas sem baixar o acervo inteiro.

### 5.4 Independência do pipeline DJEN

O crawl do JURIS não altera `sync-manifest.csv`. O cruzamento com o DJEN
(§ 2) é uma análise downstream opcional, não um requisito de ingestão.

### 5.5 Sem scraping do HTML do portal

O portal `juris.tjro.jus.br` é um frontend Angular que não serve dados
estruturados. Toda a ingestão usa exclusivamente a API REST JSON descrita
em § 3.

## 6. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| API retorna HTTP 500 com `tipo` como string | `client.py` sempre serializa `tipo` como array |
| Filtro de data server-side retorna 500 | Filtro de data aplicado client-side; pool aumentado |
| Célula tipo × mês supera 400 docs | Sub-partição automática por classe via agregações |
| Inteiro teor vazio ou ausente | Registrar `texto_limpo = ""` e logar; não abortar |
| Rate limiting / bloqueio por IP | Backoff exponencial + intervalo mínimo entre requests (0,5 s) |
| Documento atualizado muda conteúdo sem mudar ID | Re-extração mensal com `updated_at` como tiebreaker; snapshot consolidado sempre sobrescreve |
| IA rejeita Parquet como formato não reconhecido | Incluir `mediatype: data` e `format: Parquet` nos metadados do item |

## 7. Fora de escopo

- Outros tribunais (TRT14, TRF1, etc.) — podem reutilizar o mesmo padrão via
  RFC subsequente se tiverem API compatível.
- Busca full-text no dashboard (requer índice dedicado, fora do escopo do
  Parquet + DuckDB atual).
- Download dos PDFs originais linkados no portal.
- Cruzamento automático com o `sync-manifest.csv` do DJEN.

## 8. Critérios de aceitação

- [ ] `tjro-juris-manifest.csv` controla o estado de cada célula
  `(tipo, mes_ano)`.
- [ ] Items `tjro-juris-AAAA` no IA contêm os Parquets mensais e o snapshot
  anual consolidado.
- [ ] Nenhum `id_documento` duplicado no snapshot consolidado.
- [ ] Três queries renderizadas em `web/public/data/juris_*.json`.
- [ ] `uv run ruff check` e `uv run pytest -q` passam.
- [ ] CLI: `uv run tjro-juris crawl` e `uv run tjro-juris upload` funcionam de
  ponta a ponta.
- [ ] Skill `python .claude/skills/juris-tjro/scripts/juris.py buscar "teste"`
  retorna resultados sem erro.

## 9. Referências

- Endpoint de busca: `POST https://juris-back.tjro.jus.br/search/varios_parametros/`
- Portal: `https://juris.tjro.jus.br/jurisprudencia/`
- Skill interativa: `.claude/skills/juris-tjro/SKILL.md`
- Script CLI (stdlib-only): `.claude/skills/juris-tjro/scripts/juris.py`
- Padrão de upload IA: `src/djen_backup/archive.py`
- Padrão de manifest: `src/djen_backup/manifest.py`
- Padrão de query contract: `web/src/queries/README.md`
