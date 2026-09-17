---
type: AgentReading
id: "2026-09-17-exciting-mccarthy-726qh5-reading-claude-md"
run_id: "2026-09-17-exciting-mccarthy-726qh5"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "CLAUDE.md documenta apenas src/djen_backup (motor de sync DJEN/IA) e web/src/queries/*.qmd (contrato de dados do frontend) como areas de dominio formais; a linhagem do corpus de treino do segmentador (#1050, src/segmenter_dataset, scripts/*segmenter*) fica fora do mapa de arquivos mas segue as regras gerais de estilo (ruff estrito, TRY300/301/401, proibicao de except Exception amplo fora do bulkhead ADR-0011, Python 3.12+, uv run ruff check/format --check/pytest -q antes de commitar)."
---

# Leitura: CLAUDE.md

CLAUDE.md descreve dois runtimes formais: `src/djen_backup` (engine de
sincronizacao DJEN -> Internet Archive, `sync-manifest.parquet` como
fonte de verdade, distincao critica `djen_raw` transporte vs
`djen_status` veredito derivado, 403 nunca e absent) e
`web/src/queries/*.qmd` (contratos de query do frontend renderizados
por `scripts/render_queries.py`). Nenhuma das duas areas e onde esta
rodada provavelmente trabalha: a linhagem ativa e nao-bloqueada
identificada nas leituras de issues/PRs (corpus de treino do
segmentador, issue #1050, RFC 0012) vive em `src/segmenter_dataset` e
`scripts/*segmenter*`, fora do mapa de arquivos documentado aqui, mas
ainda sujeita as regras gerais: ruff estrito (sem ignores alem dos ja
documentados), TRY300/TRY301/TRY401 (raises extraidos para funcoes
internas), proibicao de `except Exception` amplo fora de um bulkhead
citando ADR-0011, Python 3.12+ com `from __future__ import annotations`,
e a checklist "Before committing" (`uv run ruff check`,
`uv run ruff format --check`, `uv run pytest -q`). Nenhuma mudanca
planejada para `djen_backup` ou para os contratos `.qmd` do frontend
nesta rodada.
