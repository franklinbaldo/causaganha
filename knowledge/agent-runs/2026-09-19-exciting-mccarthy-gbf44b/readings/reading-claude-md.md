---
type: AgentReading
id: "2026-09-19-exciting-mccarthy-gbf44b-reading-claude-md"
run_id: "2026-09-19-exciting-mccarthy-gbf44b"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "CLAUDE.md documenta apenas djen_backup (motor de sincronizacao) e o pipeline .qmd do frontend como areas de dominio; a linhagem do corpus do segmentador (#1050, src/segmenter_dataset, scripts/*segmenter*, data/segmenter*) fica fora do mapa de arquivos, mas continua sujeita as regras gerais de estilo (ruff estrito, TRY300/301/401, proibicao de except Exception amplo fora do bulkhead ADR-0011, Python 3.12+, uv run ruff check/format --check + uv run pytest -q antes de commitar)."
---

# Leitura: CLAUDE.md

CLAUDE.md descreve dois runtimes formais: `src/djen_backup` (motor de
sincronizacao DJEN/Internet Archive, `sync-manifest.parquet` como fonte
de verdade, distincao critica `djen_raw` transporte vs `djen_status`
derivado, disciplina sobre 403 vs 404/400/200-sem-URL) e
`web/src/queries/*.qmd` (contrato de dados do frontend, `render_queries.py`,
`contracts.ts`). Nenhum dos dois e onde esta rodada trabalha -- a
linhagem selecionada (corpus de treino do segmentador, issue #1050, RFC
0012) vive em `src/segmenter_dataset`/`scripts/*segmenter*`/
`data/segmenter*`, fora do mapa de arquivos documentado no CLAUDE.md,
mas ainda sujeita as regras gerais de estilo do arquivo: rodar
`uv run ruff check`, `uv run ruff format --check` e `uv run pytest -q`
antes de commitar; TRY300/TRY301/TRY401 extraindo raises para funcoes
internas; e a proibicao de `except Exception` amplo fora de um bulkhead
documentado por ADR (nao esperado nesta rodada, que reusa
`scripts/ingest_djen_sample_technique1_batch.py` ja existente sem tocar
em worker pools do djen_backup). Nenhuma mudanca de producao planejada
para `djen_backup` ou `web` nesta rodada. A secao "Antes de committar"
do CLAUDE.md tambem documenta a boundary de CSS Panda/`--cg-*`, sem
relevancia para este trabalho (nenhum arquivo `.astro`/`.svelte` sera
tocado).
