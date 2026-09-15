---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-f0q3d4-reading-claude-md"
run_id: "2026-09-15-exciting-mccarthy-f0q3d4"
source: "CLAUDE.md"
finding: "Regras de correção do djen-backup (403 != absent, 200 sem URL = absent), fronteira Panda/CSS legado, e estilo (ruff estrito, TRY300/301/401, sem except Exception amplo) seguem valendo como sempre. Nenhuma mudança de política desde a última rodada que li isto."
---

# Leitura: CLAUDE.md

Reconfirmado o conteúdo do guia do projeto: arquitetura djen-backup
(`sync-manifest.parquet` como fonte única, `djen_raw` é o status HTTP bruto,
nunca um veredito), contratos de consulta do frontend (`.qmd` → JSON via
`scripts/render_queries.py`), fronteira Panda CSS vs. bridge legado em
`index.css`, e o piso de pre-commit (`ruff check`, `ruff format --check`,
`pytest -q`). Nada disso mudou desde as rodadas anteriores desta linhagem;
nenhuma ação decorre diretamente desta leitura além de manter as mesmas
convenções ao tocar código nesta rodada.
