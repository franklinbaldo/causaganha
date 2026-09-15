---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-7drjlg-reading-claude-md"
run_id: "2026-09-15-exciting-mccarthy-7drjlg"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "Guia do repositório: backend Python (src/causaganha, src/djen_backup) + frontend web/ (Astro+Svelte). djen-backup é o motor de sincronização DJEN->Internet Archive (ADR 0012, sync-manifest.parquet como fonte de verdade). Regras de correção DJEN (403 nunca é ausente; 200 sem URL de download é ausente). Fronteira CSS Panda vs. bridge de compatibilidade em index.css. Regras de estilo: ruff estrito, sem except Exception amplo salvo bulkhead documentado em ADR 0011, TRY300/301/401. Comandos: ruff check, ruff format --check, pytest -q antes de commitar. Nenhuma seção trata do segmentador/OPF -- essa governança vive em docs/rfc/0012."
---

# Leitura: CLAUDE.md

Confirma que o trabalho desta rodada, se tocar `src/djen_backup` ou `web/`, deve seguir as regras de correção DJEN (403≠ausente, 200-sem-URL=ausente) e a fronteira CSS Panda. Nenhuma dessas áreas é o alvo principal desta rodada (ver goal), mas ficam registradas como restrições vigentes. O piso de verificação pré-commit (`ruff check`, `ruff format --check`, `pytest -q`) é o mesmo aplicado ao trabalho real desta rodada em `src/segmenter_dataset/`/`scripts/`.
