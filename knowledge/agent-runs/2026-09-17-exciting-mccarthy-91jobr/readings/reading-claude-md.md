---
type: AgentReading
id: "2026-09-17-exciting-mccarthy-91jobr-reading-claude-md"
run_id: "2026-09-17-exciting-mccarthy-91jobr"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "CLAUDE.md documenta apenas os dois runtimes formais (djen_backup e o pipeline .qmd do frontend); a linhagem do corpus do segmentador (#1050, data/segmenter*, scripts/*segmenter*) segue fora do mapa de arquivos, mas sujeita as mesmas regras gerais de estilo (ruff estrito, TRY300/301/401, proibicao de except Exception amplo fora de bulkhead ADR-0011, Python 3.12+, checks antes de commitar)."
---

# Leitura: CLAUDE.md

CLAUDE.md descreve `src/djen_backup` (motor de sincronizacao DJEN/Internet
Archive, `sync-manifest.parquet` como fonte de verdade, distincao
`djen_raw` vs `djen_status`) e `web/src/queries/*.qmd` (contrato de dados
do frontend) como as duas areas de dominio documentadas. A linhagem
selecionada nesta rodada (corpus de treino do segmentador, issue #1050)
continua fora do mapa de arquivos do CLAUDE.md, mas ainda sujeita as
regras gerais de estilo: "Antes de commitar" (`uv run ruff check`,
`uv run ruff format --check`, `uv run pytest -q`), TRY300/TRY301/TRY401,
e a proibicao de `except Exception` amplo fora de um bulkhead documentado
por ADR. Nenhuma mudanca planejada em `djen_backup` ou `web` nesta
rodada.
