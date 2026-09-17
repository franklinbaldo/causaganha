---
type: AgentReading
id: "2026-09-17-exciting-mccarthy-epgxv2-reading-claude-md"
run_id: "2026-09-17-exciting-mccarthy-epgxv2"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "CLAUDE.md documenta os dois runtimes formais do repositorio (djen_backup e o pipeline .qmd do frontend); a linhagem do corpus do segmentador (#1050, src/segmenter_dataset e scripts/*segmenter*) fica fora do mapa de arquivos documentado, mas continua sujeita as regras gerais de estilo (ruff estrito, TRY300/301/401, proibicao de except Exception amplo fora de bulkhead ADR-0011, Python 3.12+, checks antes de commitar)."
---

# Leitura: CLAUDE.md

CLAUDE.md descreve `src/djen_backup` (motor de sincronizacao DJEN/Internet
Archive, `sync-manifest.parquet` como fonte de verdade, distincao
`djen_raw` vs `djen_status`) e `web/src/queries/*.qmd` (contrato de dados
do frontend, `render_queries.py`) como as duas areas de dominio
documentadas neste arquivo. Nenhuma das duas e onde a rodada atual
trabalha -- a linhagem selecionada (corpus de treino do segmentador,
issue #1050, RFC 0012) vive em `src/segmenter_dataset`/`scripts/*segmenter*`/
`data/segmenter*`, fora do mapa de arquivos do CLAUDE.md, mas ainda sujeita
as regras gerais de estilo: "Antes de committar" (`uv run ruff check`,
`uv run ruff format --check`, `uv run pytest -q`), TRY300/TRY301/TRY401
extraindo raises para funcoes internas, e a proibicao de `except Exception`
amplo fora de um bulkhead documentado por ADR (nao esperado nesta rodada,
que reusa `scripts/ingest_djen_sample_technique1_batch.py` ja existente
sem tocar em worker pools do djen_backup). Nenhuma mudanca de producao
planejada para `djen_backup` ou `web` nesta rodada.
