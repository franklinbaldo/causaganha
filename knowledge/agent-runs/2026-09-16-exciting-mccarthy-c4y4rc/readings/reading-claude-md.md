---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-c4y4rc-reading-claude-md"
run_id: "2026-09-16-exciting-mccarthy-c4y4rc"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "Sem mudança de política desde a última leitura desta linhagem (2hb3sq): regras djen-backup (sync-manifest.parquet como fonte única, djen_raw != veredito de disponibilidade, 403 != absent), fronteira Panda/CSS (3 ilhas Svelte legadas), e estilo (ruff estrito, TRY300/301/401, sem except Exception amplo fora do bulkhead ADR 0011) seguem valendo. Nenhuma delas é tocada diretamente pelo trabalho desta rodada (src/segmenter_dataset), mas a regra de estilo se aplica a qualquer script novo."
---

# Leitura: CLAUDE.md

Reconfirmado o guia do projeto na íntegra: arquitetura djen-backup (engine
de sync com 3 pools de workers, `sync-manifest.parquet` no IA como fonte
única de verdade de estado de coleta), contratos de consulta `.qmd` do
frontend, fronteira Panda CSS vs. bridge legado em `index.css`, e o piso de
pre-commit (`uv run ruff check`, `uv run ruff format --check`, `uv run
pytest -q`). Nada disso é alterado por esta rodada, que trabalha em
`src/segmenter_dataset`/`scripts/segmenter_governance_status.py` — mas a
proibição de `except Exception` amplo fora do bulkhead documentado (ADR
0011) e as regras TRY300/301/401 se aplicam a qualquer trecho novo.
