---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-96cgqx-reading-claude-md"
run_id: "2026-09-16-exciting-mccarthy-96cgqx"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "CLAUDE.md documenta as duas superficies de runtime (djen_backup em src/djen_backup, frontend em web/ com contratos .qmd) e regras gerais de estilo (Ruff estrito, TRY300/301/401, sem except Exception amplo fora de bulkhead ADR 0011, Python 3.12+ com | unions). Nenhuma das duas superficies documentadas e a area de trabalho desta rodada (issue #1050, corpus real do segmentador, vive em src/segmenter_dataset/scripts/*segmenter*/data/segmenter*, fora do escopo descrito mas sujeito as mesmas regras de estilo e ao checklist 'Antes de commitar' (ruff check, ruff format --check, pytest -q)."
---

# Leitura: CLAUDE.md

CLAUDE.md descreve o sistema de sincronizacao DJEN/Internet Archive
(`src/djen_backup`) e o contrato de queries do frontend
(`web/src/queries/*.qmd`) como as duas areas de dominio documentadas.
Nenhuma mudanca de producao planejada para `djen_backup` ou `web` nesta
rodada -- o trabalho de continuidade (corpus real do segmentador, #1050)
fica fora do escopo descrito no CLAUDE.md, mas as regras gerais de estilo
(Ruff estrito com TRY300/301/401, `except Exception` so dentro de
bulkhead documentado por ADR, `from __future__ import annotations`,
checklist "Antes de commitar") se aplicam a qualquer script tocado.
