---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-b3xdwp-reading-claude-md"
run_id: "2026-09-15-exciting-mccarthy-b3xdwp"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "Guia do repositório: backend Python (src/causaganha, src/djen_backup) + frontend web/ (Astro+Svelte). djen-backup é o motor de sincronização DJEN->Internet Archive (ADR 0012, sync-manifest.parquet como fonte de verdade); contratos de query .qmd para o frontend; fronteira CSS Panda vs. bridge de compatibilidade em index.css; regras de estilo (ruff estrito, sem except Exception amplo salvo bulkhead ADR 0011, TRY300/301/401); comandos de pré-commit (ruff check, ruff format --check, pytest -q). Nenhuma seção trata do segmentador/OPF/RFC 0012 -- essa governança vive em docs/rfc/0012 e em src/segmenter_dataset/, fora do escopo direto deste arquivo, mas o piso de verificação pré-commit é o mesmo para qualquer mudança no repositório."
---

# Leitura: CLAUDE.md

Mesmo piso confirmado pela linhagem inteira de rodadas de hoje (bueov4 até
2cjjig): nada neste arquivo trata do segmentador diretamente, mas
`ruff check`, `ruff format --check` e `pytest -q` continuam valendo para
qualquer mudança que esta rodada produza, incluindo dados/documentação sob
`data/segmenter/` e `knowledge/agent-runs/`.
