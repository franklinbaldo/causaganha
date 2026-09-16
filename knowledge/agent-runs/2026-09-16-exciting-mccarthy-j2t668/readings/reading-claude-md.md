---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-j2t668-reading-claude-md"
run_id: "2026-09-16-exciting-mccarthy-j2t668"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "CLAUDE.md documents two runtime surfaces (djen_backup sync engine and the web frontend query-contract pipeline); neither is touched by this round's selected work. The segmenter training-corpus lineage (#1050) lives outside CLAUDE.md's documented domains but is still subject to its general style rules (Ruff strict, TRY300/301/401, no broad except Exception outside an ADR-0011 bulkhead, Python 3.12+ with | unions, ruff check/format/pytest before committing)."
---

# Leitura: CLAUDE.md

CLAUDE.md descreve `src/djen_backup` (motor de sincronizacao DJEN/Internet
Archive, manifest parquet como fonte de verdade) e `web/src/queries/*.qmd`
(contrato de dados do frontend) como as duas areas de dominio documentadas.
Nenhuma das duas e onde esta rodada trabalha -- o trabalho selecionado
(corpus de treino do segmentador, issue #1050) vive em
`src/segmenter_dataset`/`scripts/*segmenter*`/`data/segmenter*`, fora do
mapa de arquivos do CLAUDE.md, mas ainda sujeito as regras gerais de estilo
("Antes de committar": `uv run ruff check`, `uv run ruff format --check`,
`uv run pytest -q") e a proibicao de `except Exception` amplo fora de um
bulkhead documentado por ADR (nao esperado neste round, que reusa scripts
ja existentes sem tocar em worker pools). Nenhuma mudanca de producao
planejada para `djen_backup` ou `web` nesta rodada.
