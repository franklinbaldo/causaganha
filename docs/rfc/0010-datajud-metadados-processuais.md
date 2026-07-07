# RFC 0010 — DataJud: capa e movimentação oficiais como espinha do processo

- **Status:** Proposto (implementação por subagent neste ciclo)
- **Data:** 2026-07-08
- **Depende de:** RFC 0005 (processo como recurso), RFC 0007 (contratos fail-loud),
  RFC 0008 (padrão de módulo-fonte + workflow dispatch)
- **Origem:** skill `datajud` do owner (cliente CLI da API Pública, com as armadilhas
  da API já mapeadas em produção)

## 1. Resumo executivo

A API Pública do DataJud (CNJ) expõe **metadados oficiais** de processos de todos os
tribunais — capa (classe, assuntos, órgão julgador, grau, datas, sigilo) e **linha de
movimentação** (tabelas processuais unificadas) — indexados em Elasticsearch, um índice
por tribunal (`api_publica_tjro`, `api_publica_stj`, …). **Não há inteiro teor.**

Para o causaganha isso é a peça que faltava no RFC 0005: DJEN dá a *publicação*, JURIS/STJ
dão o *teor*, e o DataJud dá a **capa canônica e a tramitação** — tudo unido pelo número
CNJ de 20 dígitos. Com ele, `processos_unificados` ganha classe/assunto/órgão oficiais,
data de ajuizamento e o estado da tramitação (sentença, trânsito em julgado, baixa).

## 2. Princípio de escopo: enriquecer, não rastrear

O acervo nacional tem milhões de processos; não vamos espelhar o DataJud. O pipeline é
**demand-driven**: a lista de CNJs de entrada vem dos processos que o causaganha já
conhece (parquets `processos_unificados`/fontes DJEN, JURIS, STJ). Para cada CNJ,
buscamos capa + movimentos (todos os graus) e persistimos. Um modo secundário `facetas`
(agregações por classe/órgão/grau) alimenta estatísticas de acervo sem baixar documentos.

## 3. Desenho

### 3.1 Módulo `src/datajud/` (espelha `stj_acordaos`/`tjro_juris`)

- `client.py` — cliente httpx da API (`POST {BASE}/api_publica_{sigla}/_search`), com:
  - retry/backoff (padrão `djen_backup/retry.py`) para **os dois sabores de rate limit**:
    HTTP 429 do gateway **e** HTTP 200 com `es_rejected_execution_exception` no corpo
    (mesma classe de armadilha do "200 Sem comunicações" do DJEN — status não é veredito;
    inspecione o corpo);
  - `track_total_hits: true` sempre (sem isso o total satura em 10.000/`gte`);
  - campos textuais via `.keyword` (`grau.keyword`, `classe.nome.keyword`, …) em
    sort/term/agg — o campo cru é `text` e dá HTTP 400;
  - `dataAjuizamento` é string de **14 dígitos** (`AAAAMMDDHHMMSS`) — ranges de data
    normalizados para cobrir o dia inteiro;
  - busca por lote de CNJs (`terms` em `numeroProcesso`, paginada) — nunca 1 request/CNJ;
  - HTTP 401 → erro nominal instruindo atualizar a chave (o CNJ pode trocá-la; fonte:
    https://datajud-wiki.cnj.jus.br/api-publica/acesso/).
- `models.py` — capa + movimento (pydantic), preservando `codigo`/`nome` tabelados.
- `dedup.py` — **multi-grau**: o mesmo CNJ aparece em documentos separados por grau
  (o `_id` codifica `{TRIBUNAL}_{classe}_{grau}_{orgao}_{numero}`). Chave natural =
  `(numeroProcesso, grau, orgaoJulgador.codigo)`; entre versões do mesmo doc vence
  `dataHoraUltimaAtualizacao` mais recente.
- `manifest.py` — CSV de estado por CNJ consultado (`cnj, tribunal, docs, consultado_em,
  status`), padrão dos manifests existentes; permite re-runs incrementais (re-consultar
  só o que está velho ou ausente).
- `archive.py` — parquet(s) → item IA `datajud-{tribunal}` (capa e movimentos em arquivos
  separados: `datajud-capa-{tribunal}.parquet`, `datajud-movimentos-{tribunal}.parquet`),
  reutilizando as práticas de `stj_acordaos/archive.py` (httpx, `x-archive-meta-*`,
  percent-encode `uri(...)` para não-ASCII, retry).
- `__main__.py` — CLI Typer: `enrich` (lê CNJs dos parquets de fontes → consulta →
  parquet → IA), `facetas` (agregações), `status`.
- **Chave da API:** a pública documentada pelo CNJ, como default em constante, com
  override por env `DATAJUD_API_KEY` (rotação sem mudar código).
- **Cortesia:** rate interno (aiolimiter, já dependência) e pausa entre lotes; a fila do
  ES do CNJ enche fácil.

### 3.2 Reconciliação (RFC 0005)

`scripts/reconcile_processos.py` ganha a quarta fonte: join por CNJ com a capa DataJud →
`processos_unificados` recebe `classe_oficial`, `assuntos`, `orgao_julgador`, `grau`,
`data_ajuizamento`, `ultima_atualizacao`, `tem_datajud`. Movimentos ficam fora do join
(tabela própria, consultável por CNJ).

### 3.3 Contratos de dados (RFC 0007)

Novos `.qmd`, todos `optional: true` (o parquet pode não existir ainda):
`datajud_totals` (CNJs enriquecidos, cobertura por tribunal), `datajud_classes`
(distribuição por classe oficial), e extensão de `processos_multi_fonte` com a flag
DataJud. Tipos correspondentes em `web/src/lib/data/contracts.ts` (RFC 0009).

### 3.4 Operação (padrão RFC 0008)

Workflow `datajud-enrich.yml` **workflow_dispatch apenas** (inputs: tribunal, limite de
CNJs, janela de re-consulta). Cron é decisão do owner após rodadas manuais — o rate
limit do CNJ é a restrição dominante.

## 4. O que NÃO fazer

- **Não buscar teor** — o DataJud não tem; teor continua vindo de JURIS/STJ.
- **Não espelhar acervo** — só CNJs conhecidos (+ facetas agregadas).
- **Não tratar HTTP 200 como sucesso sem inspecionar o corpo** (rejeição do ES vem em 200).
- **Não usar campos `text` crus** em sort/term/agg — sempre `.keyword`.
- **Não paralelizar agressivamente** — backoff + respiro entre lotes.

## 5. Critérios de aceitação

- `uv run pytest -q` verde com suíte nova (`tests/datajud/`): os dois sabores de rate
  limit (429 e ES-rejection-em-200), normalização de datas 14 dígitos, dedup multi-grau,
  lote de CNJs, montagem de parquet, headers IA. Zero rede real (respx).
- `enrich --limit N --skip-upload` funcional ponta a ponta contra fixtures.
- `.qmd` novos passam `render_queries.py --check`; contratos Zod tipados no web.
- Workflow dispatch-only validado; ruff/vulture/format verdes.

## 6. Riscos

- **Chave pública trocada pelo CNJ** → 401 nominal + env override; baixo impacto.
- **Rate limit em runs grandes** → lotes pequenos, manifest incremental re-executável;
  um run interrompido retoma de onde parou.
- **Volume de movimentos** (centenas por processo) → parquet separado da capa; a capa
  continua leve para joins.
