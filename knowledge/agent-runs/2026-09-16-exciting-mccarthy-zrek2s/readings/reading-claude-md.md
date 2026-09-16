---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-zrek2s-reading-claude-md"
run_id: "2026-09-16-exciting-mccarthy-zrek2s"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Repo has two runtime surfaces (Python backend src/causaganha + src/djen_backup, web frontend em web/). djen_backup usa sync-manifest.parquet como fonte unica de verdade para status de coleta DJEN/IA; nao e area tocada por este round. As regras de estilo relevantes (Ruff estrito, TRY300/301/401, sem except Exception amplo fora de bulkhead documentado por ADR 0011, python 3.12+ com | unions) se aplicam a qualquer script novo escrito neste round."
---

# Leitura: CLAUDE.md

CLAUDE.md descreve o sistema de sincronizacao DJEN/Internet Archive
(`src/djen_backup`) e o contrato de queries do frontend (`web/src/queries/*.qmd`)
como as duas areas de dominio documentadas -- nenhuma das duas e onde este
round trabalha (issue #1050, corpus de treino do segmentador, vive em
`src/segmenter_dataset`/`scripts/*segmenter*`/`data/segmenter*`, fora do
escopo descrito no CLAUDE.md mas sujeito as mesmas regras gerais de estilo
("Antes de commitar": ruff check, ruff format --check, pytest -q). Nenhuma
mudanca de producao planejada para djen_backup ou web nesta rodada.
