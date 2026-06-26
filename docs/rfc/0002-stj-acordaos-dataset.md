# RFC 0002 — Ingestão do Dataset de Espelhos de Acórdãos do STJ

- **Status:** Proposto
- **Data:** 2026-06-26
- **Escopo:** Ingestão, arquivamento e consulta dos espelhos de acórdãos da
  Primeira Seção do STJ a partir do portal de dados abertos do tribunal.

## 1. Resumo executivo

O STJ disponibiliza no portal de dados abertos
(`https://dadosabertos.web.stj.jus.br/dataset/espelhos-de-acordaos-primeira-secao`)
arquivos JSON mensais com os **espelhos de acórdãos** — fichas estruturadas de
decisões colegiadas que o tribunal considera inovadoras em tese jurídica. Cada
registro contém classe processual, relator, ementa, tese jurídica, referências
legislativas, precedentes similares e data de publicação, entre outros campos.

Este RFC propõe:

1. Um **módulo de ingestão** (`src/stj_acordaos/`) que baixa, deduplica e
   arquiva os arquivos JSON no Internet Archive.
2. Um **modelo de dados** mínimo mapeado dos 20 campos do dicionário oficial.
3. **Query contracts** (`.qmd`) para expor estatísticas básicas no dashboard
   existente.

A integração é independente do pipeline DJEN e não requer alteração no
`sync-manifest.csv`.

## 2. Motivação

O DJEN já captura *quando* uma decisão foi publicada (caderno diário). O
dataset de espelhos do STJ adiciona o *conteúdo jurídico estruturado* dessa
decisão: tese estabelecida, tema repetitivo, classe processual, relator e
precedentes associados. Cruzar as duas fontes permite:

- Identificar quais cadernos DJEN contêm decisões de tese repetitiva do STJ.
- Calcular métricas de tempo (data da decisão → data de publicação no DJEN).
- Servir busca por tese jurídica e tema repetitivo no dashboard.

O dataset é liberado sob **CC-BY**, sem restrições de uso.

## 3. Fonte de dados

| Propriedade | Valor |
|---|---|
| Portal | `https://dadosabertos.web.stj.jus.br` |
| Dataset ID | `a96a175b-a54b-4bfd-82b8-fcd7cc0200bc` |
| Seção | Primeira Seção |
| Formato | JSON (um arquivo por extração mensal) |
| Nomenclatura | `YYYYMMDD.json` (data de extração) |
| Histórico ZIP | `20220508.zip` (acervo completo até mai/2022) |
| Dicionário | `dicionario-espelhodoacordao.csv` |
| Licença | Creative Commons Attribution (CC-BY) |
| Última atualização | jun/2026 |
| Frequência | Mensal |

### 3.1 Estrutura de arquivos

O portal mantém ~48 arquivos JSON mensais (mai/2022 – jun/2026) mais o ZIP
histórico. **O primeiro arquivo contém o acervo completo; os demais contêm
apenas atualizações.** Um mesmo acórdão pode aparecer em mais de um arquivo
quando sofre alteração posterior — a deduplicação é obrigatória e usa o campo
`id` como chave primária.

### 3.2 Modelo de dados

Campos conforme `dicionario-espelhodoacordao.csv`:

| Campo | Descrição |
|---|---|
| `id` | Chave primária no banco de jurisprudência do STJ |
| `numeroProcesso` | Número do processo no STJ |
| `numeroRegistro` | Número de registro do caso |
| `siglaClasse` | Sigla da classe processual |
| `descricaoClasse` | Nome completo da classe processual |
| `nomeOrgaoJulgador` | Órgão colegiado julgador |
| `ministroRelator` | Ministro relator |
| `ementa` | Resumo do conteúdo da decisão (elaborado pelo relator) |
| `tipoDeDecisao` | Singular ou colegiada |
| `dataDecisao` | Data do julgamento |
| `decisao` | Dispositivo, votação e informações processuais |
| `jurisprudenciaCitada` | Precedentes citados, agrupados por matéria |
| `notas` | Índice de assuntos e modificações relevantes |
| `informacoesComplementares` | Informações adicionais sobre teses decididas |
| `termosAuxiliares` | Termos alternativos de busca (tesauro jurídico) |
| `teseJuridica` | Tese jurídica fixada em precedentes qualificados |
| `tema` | Número do tema repetitivo (precedente de gestão) |
| `referenciasLegislativas` | Atos normativos relacionados às teses analisadas |
| `acordaosSimilares` | Decisões relacionadas com teses semelhantes |
| `dataPublicacao` | Data e fonte de publicação |

## 4. Proposta técnica

### 4.1 Estrutura de diretórios

```
src/stj_acordaos/
├── __init__.py
├── __main__.py          — CLI (Typer): download, upload, status
├── client.py            — HTTP client para o portal de dados abertos do STJ
├── manifest.py          — ManifestSTJ: controla quais arquivos foram baixados/enviados
├── dedup.py             — Deduplicação por `id` via DuckDB em memória
└── archive.py           — Upload para Internet Archive (reutiliza padrões de djen_backup)

scripts/
└── stj_render_queries.py  — Renderiza .qmd específicos do STJ para JSON

web/src/queries/
├── stj_totals.qmd         — Contagem geral de acórdãos
├── stj_relatores.qmd      — Ranking de relatores por volume
└── stj_temas.qmd          — Distribuição por tema repetitivo
```

### 4.2 Manifest do STJ

Arquivo separado do `sync-manifest.csv` existente: `stj-manifest.csv`.

| Coluna | Descrição |
|---|---|
| `arquivo` | Nome do arquivo JSON (ex.: `20260531.json`) |
| `data_extracao` | Data de extração (do nome do arquivo) |
| `ia_status` | `""` \| `"uploaded"` |
| `n_registros` | Quantidade de registros no arquivo |
| `updated_at` | Timestamp da última atualização da linha |

O IA item de destino será `stj-acordaos-primeira-secao` (um item único,
análogo ao padrão `djen-{tribunal}-{year}`, mas sem partição por ano dado
o volume menor).

### 4.3 Fluxo de ingestão

```
1. Descoberta
   └── GET portal/dataset → lista de recursos (nome + URL de download)

2. Download incremental
   └── Para cada arquivo ausente no manifest (ou com ia_status vazio):
       └── GET URL → salva JSON local

3. Deduplicação
   └── DuckDB: COPY JSON → tabela, SELECT DISTINCT ON (id) ORDER BY data_extracao DESC
   └── Gera `acordaos-dedup-YYYYMMDD.parquet` (snapshot consolidado)

4. Upload para Internet Archive
   └── Envia arquivos JSON originais + parquet consolidado
   └── Marca ia_status = "uploaded" no manifest

5. Render queries
   └── stj_render_queries.py lê parquet → escreve JSONs em web/public/data/
```

### 4.4 Nomenclatura no Internet Archive

- **Item**: `stj-acordaos-primeira-secao`
- **Arquivos JSON originais**: `stj-YYYYMMDD.json`
- **Snapshot consolidado**: `stj-acordaos-dedup-YYYYMMDD.parquet`
  (substituído a cada ciclo de ingestão)

### 4.5 Integração com o dashboard

Três query contracts novos (`.qmd`):

- **`stj_totals.qmd`**: total de acórdãos, total de temas repetitivos,
  data mais recente.
- **`stj_relatores.qmd`**: top-20 relatores por volume de espelhos.
- **`stj_temas.qmd`**: distribuição por `tema` (número do tema repetitivo),
  filtrável por classe processual.

A página `/stj` do dashboard consumirá esses três endpoints.

## 5. Decisões de design

### 5.1 Item único no IA vs. partição por ano

O acervo completo tem ~48 arquivos JSON mensais. Particionar por ano geraria
~5 itens pouco densos. Item único simplifica a descoberta e o upload
incremental, sem violação das políticas do IA.

### 5.2 Deduplicação obrigatória antes de qualquer análise

O portal alerta que o mesmo acórdão pode aparecer em múltiplos arquivos
mensais. A regra de deduplicação é: **manter a versão mais recente** (`id`,
`MAX(data_extracao)`). O parquet consolidado é a fonte de verdade para
queries; os JSONs originais são arquivados como-is.

### 5.3 Sem alterar o sync-manifest.csv existente

O pipeline DJEN e o pipeline STJ são completamente independentes. O STJ não
usa o esquema `(tribunal, date)` do DJEN. Misturar os dois manifestos
aumentaria a complexidade sem benefício.

### 5.4 Sem API SPARQL ou endpoint de jurisprudência

O portal de dados abertos disponibiliza arquivos para download direto. Não
existe endpoint de streaming ou API consultável documentada — o modelo de
ingestão é portanto batch/pull mensal, não push/webhook.

### 5.5 Escopo inicial: apenas Primeira Seção

O STJ tem três seções e a Corte Especial. Datasets equivalentes existem para
a Segunda Seção e para a Corte Especial. Este RFC cobre apenas a Primeira
Seção para validar o padrão; as demais seções poderão ser adicionadas
seguindo o mesmo template sem alteração de arquitetura.

## 6. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| URL de download muda quando portal é atualizado | Redescoberta via scraping da página do dataset a cada ciclo |
| Portal retorna 403/503 sob carga | Retry com backoff exponencial (reutilizar `retry.py`) |
| Arquivo JSON malformado | Validação com `json.loads()` antes de persistir; pular e logar |
| Duplicatas não detectadas por `id` | Teste com amostra do acervo histórico antes do primeiro upload |
| IA rejeita item por metadados insuficientes | Incluir `subject`, `mediatype`, `description` nos headers de upload |

## 7. Fora de escopo

- Ingestão das demais seções do STJ (Segunda Seção, Corte Especial, Terceira
  Seção) — poderá ser feita em RFC subsequente com o mesmo padrão.
- OCR ou extração de texto dos PDFs linkados em `dataPublicacao`.
- Cruzamento com o `sync-manifest.csv` do DJEN (análise possível mas não
  implementada nesta RFC).
- Interface de busca full-text por `ementa` ou `teseJuridica` no dashboard.

## 8. Critérios de aceitação

- [ ] `stj-manifest.csv` persiste estado de todos os arquivos mensais.
- [ ] Item `stj-acordaos-primeira-secao` no IA contém todos os JSONs originais.
- [ ] `stj-acordaos-dedup-YYYYMMDD.parquet` reflete a deduplicação correta
  (nenhum `id` duplicado).
- [ ] Três queries renderizadas em `web/public/data/stj_*.json`.
- [ ] `uv run ruff check` e `uv run pytest -q` passam sem erros.
- [ ] CLI: `uv run stj-acordaos download` e `uv run stj-acordaos upload`
  funcionam de ponta a ponta.

## 9. Referências

- Portal: `https://dadosabertos.web.stj.jus.br/dataset/espelhos-de-acordaos-primeira-secao`
- Dataset ID no portal: `a96a175b-a54b-4bfd-82b8-fcd7cc0200bc`
- Dicionário de dados: `dicionario-espelhodoacordao.csv` (disponível no portal)
- Padrão de upload existente: `src/djen_backup/archive.py`
- Padrão de manifest existente: `src/djen_backup/manifest.py`
- Padrão de query contract: `web/src/queries/README.md`
