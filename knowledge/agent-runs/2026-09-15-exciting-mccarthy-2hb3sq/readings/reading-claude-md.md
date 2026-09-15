---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-2hb3sq-reading-claude-md"
run_id: "2026-09-15-exciting-mccarthy-2hb3sq"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "Regras de correção do djen-backup (403 != absent, 200 sem URL de download = absent), fronteira Panda/CSS legado nas 3 ilhas Svelte, e estilo (ruff estrito, TRY300/301/401, sem except Exception amplo fora do bulkhead ADR 0011) seguem valendo sem mudança de política desde as rodadas anteriores desta linhagem (yz281l, f0q3d4)."
---

# Leitura: CLAUDE.md

Reconfirmado o conteúdo do guia do projeto: arquitetura djen-backup
(`sync-manifest.parquet` como fonte única de verdade de estado de coleta,
`djen_raw` é o status HTTP bruto, nunca um veredito de disponibilidade),
contratos de consulta do frontend (`.qmd` → JSON via
`scripts/render_queries.py`), fronteira Panda CSS vs. bridge legado em
`index.css`, e o piso de pre-commit (`ruff check`, `ruff format --check`,
`pytest -q`). Nada disso é tocado pelo trabalho desta rodada (segmentador de
documentos, `src/segmenter_dataset`), mas a regra de estilo (ruff estrito,
sem `except Exception` amplo fora do bulkhead documentado) se aplica a
qualquer script novo que eu escrever.
