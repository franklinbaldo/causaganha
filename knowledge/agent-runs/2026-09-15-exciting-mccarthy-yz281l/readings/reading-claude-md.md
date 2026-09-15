---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-yz281l-reading-claude-md"
run_id: "2026-09-15-exciting-mccarthy-yz281l"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "CausaGanha arquiva comunicações judiciais (DJEN) no Internet Archive e serve um dashboard público: backend Python (src/causaganha, src/djen_backup), frontend Astro 7 + Svelte 5 (web/). Regras centrais: sync-manifest.parquet no IA é a fonte única de verdade; djen_raw é sempre o código HTTP bruto, nunca um veredito -- 200 com corpo 'Sem comunicações' é absent, não available; 403 nunca é absent (rate limit); não confiar em absent de rodadas antigas. Upload IA usa httpx (nunca boto3), lock por item + token bucket em archive.py, ItemBusyError deve reenfileirar em vez de bloquear. Fronteira CSS: Panda via preset cobogo é o único sistema; index.css é ponte de compatibilidade só para 3 ilhas Svelte legadas nomeadas (ProcessoLookup, PublicationSearch, SavedConsultations) -- componentes novos não introduzem custom properties fora de panda.config.ts. Estilo: ruff estrito, sem except Exception cego fora do bulkhead ADR-0011, TRY300/301/401 aplicados, Python 3.12+ com `from __future__ import annotations`. Antes de commitar: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`. CLAUDE.md não menciona Wisk nem AgentRun -- essa governança vive só em .claude/hourly-loop.md (ver reading-okf)."
---

# Leitura de CLAUDE.md

Leitura integral nesta rodada. Nada mudou desde a última rodada (bueov4/to0ars/50ns70) que leu o mesmo arquivo: os contratos de `djen_raw`/`djen_status`, a fronteira Panda/CSS e as regras de estilo seguem idênticos. Relevante para o trabalho desta rodada (ver goals): nenhuma das regras acima bloqueia trabalhar em `src/causaganha/consolidate/exporter.py` (escrita de Parquet) nem em `scripts/benchmarks/`, e o piso de verificação pré-commit (`ruff check`, `ruff format --check`, `pytest -q`) é o mesmo usado para validar qualquer mudança nesta rodada.
