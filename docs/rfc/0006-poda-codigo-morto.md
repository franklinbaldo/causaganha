# RFC 0006 — Poda de código morto e superfície de manutenção

- **Status:** Proposto (implementação neste PR, em commits faseados)
- **Data:** 2026-07-07
- **Base:** `docs/planning/oportunidades-melhoria-2026-07.md` §2 (auditoria de alcance
  real: entry points × workflows × imports)

## 1. Resumo

O único entry point em produção é `djen-backup`. O CLI `causaganha` (~1.500 linhas) não é
invocado por nenhum workflow e é o único fio que mantém vivas ~14K linhas em
`src/causaganha` (pipeline, scoring, storage/repositories, archival, compliance, a maior
parte de analysis). Somam-se 15 scripts órfãos, 5 workflows com triggers para branches
inexistentes, logs versionados na raiz e 6 dependências pesadas sem importador vivo.

Este RFC remove tudo isso em **duas fases, commits separados**, cada uma deixando a suíte
verde. O git preserva o histórico: qualquer módulo pode voltar de forma deliberada (ex.:
se o RFC 0004 — embeddings — avançar, o stack de embeddings é restaurado de um commit
conhecido, não de memória).

## 2. Fase A — inequívoca (zero alcance, zero ambiguidade)

1. **Raiz:** deletar `server.log`, `dev_output.log`, `run_stats.json`, `ia_data.json`;
   adicionar `*.log` ao `.gitignore`.
2. **Scripts órfãos (0 referências em código, workflow ou doc):**
   `analyze_pipeline_performance.py`, `check_export_health.py`, `check_ia_credentials.py`,
   `create_sample_data.py`, `extract_local_css.py`, `fp_centroid_filter.py`,
   `laptop_service.py`, `monitor_collect.py`, `monitor_github_backfill.py`,
   `probe_tribunal_start_dates.py`, `reconcile_manifest.py`, `train_ml_from_parquets.py`,
   `validate_api_coverage.py`, `validate_system_health.py`, `verify_v2_collection.py`.
3. **Módulos órfãos de `analysis/`:** `entity_ruler.py`, `ner_pipeline.py`,
   `document_markup.py`, `api_embedder.py`, `text_truncate.py` (+ seus testes-espelho
   `test_api_embedder.py`, `test_text_truncate.py`).
4. **Workflows com trigger morto:** remover triggers `push` para branches inexistentes em
   `manifest-writeback.yml`, `roundtrip-check.yml`, `bootstrap-corpus.yml`,
   `backfill-probe.yml` (mantêm `workflow_dispatch`); deletar `recover-manifest.yml`
   (one-off autodeclarado, sem script).
5. **Dependências:** remover `spacy`, `accelerate`, `transformers` (grupo `ner` — únicos
   importadores morrem no item 3; `torch` FICA, usado por `train_decision_segmenter.py`).

## 3. Fase B — CLI `causaganha` e sua cauda

Remover, com `uv run pytest -q` verde após cada grupo:

- `src/causaganha/cli/` inteiro e o entry point `causaganha` do `pyproject.toml`.
- `pipeline/`: `analyze.py`, `analyze_parquet.py`, `collect.py`, `score.py`,
  `export_orchestrator.py`, `ia_download.py`, `ia_parquet_uploader.py`,
  `parquet_export.py`, `repositories.py`, `models.py`, `embedding_pipeline.py`
  (**`ia_s3.py` FICA** — usado por `render_manifest_parquet.py` em CI).
- `scoring/openskill.py`, `storage/repositories/`, `storage/migrations.py` + `*.sql`,
  `storage/embedding_storage.py`, `catalog/creator.py`, `archival/cold_storage.py`,
  `compliance/report.py`, `clients/` (pje, archive, constants).
- `analysis/`: tudo exceto `keyword_classifier.py`, `llm_analyzer.py`, `models.py` (vivos
  via `daily_benchmark_update --mock` em CI) e o que estes importarem transitivamente.
- Testes e scripts que só exercitam o removido.
- Dependências que ficam sem importador: `boto3`, `fpdf`, `lancedb` (extra `embeddings`),
  grupo `classify` (`sentence-transformers`, `scikit-learn`, `joblib`) — `litellm` fica se
  `llm_analyzer` o usar; `dbt-duckdb` sai do grupo dev (não há projeto dbt no repo).
- Atualizar `vulture_whitelist.py`, `CLAUDE.md` (file map) e referências quebradas
  (`benchmark_store.py:15` → `compact_benchmark.py` inexistente).

## 4. O que explicitamente NÃO sai

`src/djen_backup/` (produção), fatia viva de `src/causaganha` (`config`, `pipeline/ia_s3`,
`storage/{connection,djen_schema}`, núcleo de `consolidate/` usado por
`scripts/pipeline/consolidate.py` e `roundtrip_check.py`), `src/stj_acordaos`,
`src/tjro_juris` (RFC 0008), `data/` (usado por benchmark/segmenter), stack do segmentador
(`torch`, scripts de treino, workflows `train-segmenter`/`sample-segmenter-texts`).

## 5. Critérios de aceitação

- `uv run pytest -q`, `uv run ruff check`, `uv run ruff format --check` verdes.
- `uvx vulture src/ scripts/ vulture_whitelist.py --min-confidence 100` verde.
- Nenhum workflow referencia arquivo deletado (`grep` nos `.yml`).
- `uv sync` instala mensuravelmente menos pacotes (baseline: 251).

## 6. Riscos e reversão

Risco principal: remover algo com uso não detectado pela análise estática (ex.: invocação
manual documentada externamente). Mitigação: fases em commits separados, PR revisado pelo
owner antes do merge, histórico git como arquivo. Reversão: `git revert` do commit da fase.
