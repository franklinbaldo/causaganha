---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-k5wsee-reading-claude-md"
run_id: "2026-09-16-exciting-mccarthy-k5wsee"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "CLAUDE.md documenta duas superficies de runtime (djen_backup e web/), nenhuma das duas e onde a linhagem #1050/#1051 (corpus de treino do segmentador em src/segmenter_dataset, scripts/*segmenter*, data/segmenter*) vive -- essa area fica fora do escopo explicito do arquivo, mas as regras gerais de estilo (Ruff estrito, TRY300/301/401, sem except Exception amplo fora de bulkhead ADR 0011, Python 3.12+ com | unions, checklist 'Before committing': ruff check, ruff format --check, pytest -q) se aplicam a qualquer script tocado nesta rodada."
---

# Leitura: CLAUDE.md

Reconfirma o mesmo escopo documentado (djen-backup sync engine + contrato
de queries `.qmd` do frontend). Nenhuma mudanca planejada nesta rodada
toca `src/djen_backup` ou `web/`; o trabalho selecionado (retomar PR
#1552, corpus do segmentador) segue as regras gerais de estilo do
arquivo mas nao seu dominio especifico.
