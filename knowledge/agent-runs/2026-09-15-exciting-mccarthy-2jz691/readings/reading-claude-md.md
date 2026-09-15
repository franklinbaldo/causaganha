---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-2jz691-reading-claude-md"
run_id: "2026-09-15-exciting-mccarthy-2jz691"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "Guia do repositório: backend Python (src/causaganha, src/djen_backup) + frontend web/ (Astro+Svelte). djen-backup é o motor de sincronização DJEN->Internet Archive (ADR 0012, sync-manifest.parquet como fonte de verdade). Regras de correção DJEN (403 nunca é ausente; 200 sem URL de download é ausente). Fronteira CSS Panda vs. bridge de compatibilidade em index.css. Regras de estilo: ruff estrito, sem except Exception amplo salvo bulkhead documentado em ADR 0011, TRY300/301/401. Comandos: ruff check, ruff format --check, pytest -q antes de commitar. Nenhuma seção trata do segmentador/OPF/RFC 0012 -- essa governança vive em docs/rfc/0012 e em src/segmenter_dataset/, fora do escopo direto deste arquivo."
---

# Leitura: CLAUDE.md

Confirma o mesmo piso já registrado por rodadas anteriores da linhagem de hoje (7drjlg etc.): nenhuma seção deste arquivo trata do segmentador, que é o alvo desta rodada (continuar #1051). As regras de correção DJEN e a fronteira CSS Panda não se aplicam ao trabalho escolhido nesta rodada (src/segmenter_dataset/, scripts/, data/segmenter/), mas o piso de verificação pré-commit (ruff check, ruff format --check, pytest -q) é o mesmo aplicado a qualquer mudança no repositório.
