---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-afj2il-reading-claude-md"
run_id: "2026-09-15-exciting-mccarthy-afj2il"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "Mesmo piso confirmado por toda a linhagem de rodadas de hoje: guia cobre backend Python (src/causaganha, src/djen_backup), motor djen-backup (ADR 0012, sync-manifest.parquet como fonte de verdade, djen_raw != veredito de disponibilidade), contratos de query .qmd, fronteira CSS Panda vs. bridge de compatibilidade em index.css, e regras de estilo (ruff estrito, sem except Exception amplo salvo bulkhead ADR 0011, TRY300/301/401, pre-commit = ruff check + ruff format --check + pytest -q). Nenhuma seção trata do segmentador/OPF/RFC 0012 -- essa governança vive em docs/rfc/0012 e em src/segmenter_dataset/ -- mas o piso de verificação pré-commit vale para qualquer mudança desta rodada, incluindo dados sob data/segmenter/reviews/."
---

# Leitura: CLAUDE.md

Confirmado ao vivo nesta rodada (mesmo texto da linhagem de hoje, sem mudança): o guia do repositório não trata do segmentador diretamente, mas os comandos de pré-commit (`uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`) e a proibição de `except Exception` amplo fora do bulkhead do ADR 0011 valem para qualquer artefato tocado nesta rodada.
