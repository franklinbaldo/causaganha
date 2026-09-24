---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-mjd1vm-reading-claude-md"
run_id: "2026-09-24-exciting-mccarthy-mjd1vm"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "CLAUDE.md continua documentando apenas djen_backup e o pipeline .qmd do frontend como dominios formais; a linhagem do corpus do segmentador (#1050, src/segmenter_dataset, scripts/*segmenter*, data/segmenter*) permanece fora do mapa de arquivos, mas as regras gerais de estilo se aplicam integralmente: ruff estrito, TRY300/301/401, proibicao de except Exception amplo fora do bulkhead ADR-0011, uv run ruff check/format --check + uv run pytest -q antes de commitar."
---

# Leitura: CLAUDE.md

Sem mudanca de conteudo relevante desde a ultima leitura registrada
(fv62kx, 2026-09-20). CLAUDE.md descreve dois runtimes formais:
`src/djen_backup` (motor de sincronizacao DJEN/Internet Archive,
`sync-manifest.parquet` como fonte de verdade, distincao critica
`djen_raw` transporte vs `djen_status` derivado) e
`web/src/queries/*.qmd` (contrato de dados do frontend). O trabalho
selecionado nesta rodada (ver goals) toca `data/segmenter/annotations/*`
e `.github` CI, nenhum dos dois dominios formais -- ainda assim sujeito
as regras gerais: `uv run ruff check`, `uv run ruff format --check` e
`uv run pytest -q` antes de qualquer push. Nenhuma mudanca de producao
planejada para `djen_backup` ou `web` nesta rodada. A secao de boundary
CSS Panda/`--cg-*` nao e relevante (nenhum arquivo `.astro`/`.svelte`
sera tocado).
