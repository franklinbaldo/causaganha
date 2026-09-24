---
type: AgentReading
id: "2026-09-20-exciting-mccarthy-x3954c-reading-claude-md"
run_id: "2026-09-20-exciting-mccarthy-x3954c"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "CLAUDE.md documenta apenas djen_backup (motor de sincronizacao) e o pipeline .qmd do frontend como areas de dominio formalmente mapeadas; a linhagem do corpus do segmentador (#1050, src/segmenter_dataset, scripts/*segmenter*, data/segmenter*) -- onde esta rodada efetivamente trabalhou -- fica fora do file map, mas continua sujeita as regras gerais de estilo: uv run ruff check / ruff format --check / pytest -q antes de commitar; TRY300/TRY301/TRY401; proibicao de except Exception amplo fora de um bulkhead documentado por ADR-0011 (nao aplicavel aqui, nenhum worker pool tocado). Nenhuma das secoes especificas de djen_backup (djen_raw vs djen_status, 403 vs 404/400/200-sem-URL, per-item lock em archive.py) ou do CSS/Panda boundary do frontend e relevante para o trabalho desta rodada."
---

# Leitura: CLAUDE.md

CLAUDE.md descreve dois runtimes formais: `src/djen_backup` (motor de
sincronizacao DJEN/Internet Archive, com a distincao critica
`djen_raw` transporte vs `djen_status` derivado, e a disciplina 403
vs 404/400/200-sem-URL) e `web/src/queries/*.qmd` (contrato de dados
do frontend). Nenhum dos dois foi tocado nesta rodada.

O trabalho selecionado (ver `goal-dedup-quadratic-fix`) vive em
`src/segmenter_dataset/dedup.py` e `src/segmenter_dataset/splits.py`,
fora do file map documentado, mas ainda sob as regras gerais de estilo
do arquivo: Ruff estrito (`uv run ruff check`, `uv run ruff format
--check`), TRY300/TRY301/TRY401 (extrair raises para funcoes internas
-- nao necessario aqui, nenhuma excecao nova foi introduzida), e a
proibicao de `except Exception` amplo fora de um bulkhead documentado
por ADR (nao aplicavel: nenhum `except` foi adicionado ou alterado).
Python 3.12+, `from __future__ import annotations` -- ja presentes nos
dois arquivos tocados, preservados. Nenhuma mudanca em `djen_backup`,
`web/`, ou no boundary CSS/Panda.
