---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-f3feqb-reading-claude-md"
run_id: "2026-09-15-exciting-mccarthy-f3feqb"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "Guia do repositório: backend Python (src/causaganha, src/djen_backup) + frontend web/ (Astro+Svelte). djen-backup é o motor de sincronização DJEN->Internet Archive (ADR 0012, sync-manifest.parquet como fonte de verdade); contratos de query .qmd para o frontend; fronteira CSS Panda vs. bridge de compatibilidade em index.css; regras de estilo (ruff estrito, sem except Exception amplo salvo bulkhead ADR 0011, TRY300/301/401); comandos de pré-commit (ruff check, ruff format --check, pytest -q). Nenhuma seção trata do segmentador/OPF/RFC 0012 -- essa governança vive em docs/rfc/0012 e em src/segmenter_dataset/, fora do escopo direto deste arquivo, mas o piso de verificação pré-commit vale para qualquer mudança produzida nesta rodada, incluindo dados sob data/segmenter/."
---

# Leitura: CLAUDE.md

Mesmo piso confirmado por toda a linhagem de rodadas de hoje: nada neste
arquivo trata do segmentador diretamente, mas `ruff check`,
`ruff format --check` e `pytest -q` valem para qualquer mudança desta
rodada, incluindo dados/documentação sob `data/segmenter/` e
`knowledge/agent-runs/`.
