---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-imy2ed-reading-claude-md"
run_id: "2026-09-16-exciting-mccarthy-imy2ed"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "CLAUDE.md documenta duas superficies de runtime (djen_backup sync engine + contrato de queries .qmd do frontend web/), nenhuma das duas cobre onde a linhagem #1050/#1051 (corpus de treino do segmentador em src/segmenter_dataset, scripts/*segmenter*, data/segmenter*) vive -- essa area fica fora do escopo explicito do arquivo. As regras gerais de estilo (Ruff estrito, TRY300/301/401 aplicados, sem except Exception amplo fora do bulkhead do ADR 0011, Python 3.12+ com | unions e from __future__ import annotations, checklist 'Before committing': ruff check, ruff format --check, pytest -q) se aplicam a qualquer script tocado nesta rodada mesmo assim."
---

# Leitura: CLAUDE.md

Reconfirma o mesmo escopo documentado (djen-backup sync engine + contrato
de queries `.qmd` do frontend). O trabalho selecionado nesta rodada
(decimo lote real do corpus do segmentador para #1050) nao toca
`src/djen_backup` nem `web/`, mas segue as regras gerais de estilo do
arquivo (Ruff estrito, TRY300/301/401, sem `except Exception` amplo fora
do ADR 0011).
