---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-2cjjig-reading-claude-md"
run_id: "2026-09-15-exciting-mccarthy-2cjjig"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "Guia do repositório: backend Python (src/causaganha, src/djen_backup) + frontend web/ (Astro+Svelte). djen-backup é o motor de sincronização DJEN->Internet Archive (ADR 0012, sync-manifest.parquet como fonte de verdade). Regras de correção DJEN (403 nunca é ausente; 200 sem URL de download é ausente). Fronteira CSS Panda vs. bridge de compatibilidade em index.css. Regras de estilo: ruff estrito, sem except Exception amplo salvo bulkhead documentado em ADR 0011, TRY300/301/401. Comandos: ruff check, ruff format --check, pytest -q antes de commitar. Nenhuma seção trata do segmentador/OPF/RFC 0012 -- essa governança vive em docs/rfc/0012 e em src/segmenter_dataset/, fora do escopo direto deste arquivo."
---

# Leitura: CLAUDE.md

Mesmo piso já confirmado por toda a linhagem de rodadas de hoje: nenhuma
seção deste arquivo trata do segmentador (alvo provável desta rodada, ver
reading-issues/reading-okf). As regras de correção DJEN e a fronteira CSS
Panda não se aplicam a `src/segmenter_dataset/`, `scripts/segmenter_*` ou
`data/segmenter/`, mas o piso de verificação pré-commit (ruff check, ruff
format --check, pytest -q) é o mesmo aplicado a qualquer mudança no
repositório.
