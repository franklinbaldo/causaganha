---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-5ov0kv-reading-claude-md"
run_id: "2026-09-15-exciting-mccarthy-5ov0kv"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "Mesmo piso confirmado por toda a linhagem de rodadas de hoje: guia cobre backend Python (src/causaganha, src/djen_backup), motor djen-backup (ADR 0012, sync-manifest.parquet como fonte de verdade, djen_raw != veredito de disponibilidade -- 200 sem URL de download é absent), contratos de query .qmd, fronteira CSS Panda vs. bridge de compatibilidade em index.css, e regras de estilo (ruff estrito, sem except Exception amplo salvo bulkhead ADR 0011, TRY300/301/401, pre-commit = ruff check + ruff format --check + pytest -q). Nenhuma seção trata do segmentador/OPF/RFC 0012 -- essa governança vive em docs/rfc/0012 e em src/segmenter_dataset/ -- mas o piso de verificação pré-commit vale para qualquer mudança desta rodada, incluindo dados sob data/segmenter/reviews/."
---

# Leitura: CLAUDE.md

Lido integralmente do system prompt desta sessão. Nada mudou desde a última
reconfirmação da linhagem de hoje (yz281l, rt6d4o, ..., 6kxfkh, bc9ae6). O
comando de pré-commit (`uv run ruff check && uv run ruff format --check &&
uv run pytest -q`) e a proibição de `except Exception` amplo fora do
bulkhead do ADR 0011 valem para qualquer artefato tocado nesta rodada.
