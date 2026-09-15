---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-6d5vnd-reading-claude-md"
run_id: "2026-09-15-exciting-mccarthy-6d5vnd"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "CausaGanha arquiva comunicações judiciais (DJEN) no Internet Archive e serve um dashboard público: backend Python (src/causaganha, src/djen_backup), frontend Astro 7 + Svelte 5 (web/). sync-manifest.parquet no IA é a fonte única de verdade; djen_raw é sempre o código HTTP bruto, nunca veredito de disponibilidade (200 com corpo 'Sem comunicações' é absent); 403 nunca é absent. Upload IA usa httpx, lock por item + token bucket em archive.py. Fronteira CSS: Panda via preset cobogo é único sistema; index.css é ponte só para 3 ilhas Svelte legadas. Estilo: ruff estrito, sem except Exception cego fora do bulkhead ADR-0011, TRY300/301/401, Python 3.12+ com `from __future__ import annotations`. Pré-commit: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`. CLAUDE.md não menciona Wisk nem AgentRun -- essa governança vive só em .claude/hourly-loop.md (ver reading-okf)."
---

# Leitura de CLAUDE.md

Leitura integral nesta rodada. Nenhuma regra bloqueia o trabalho cogitado (script de benchmark em `scripts/benchmarks/`, ajuste em `docs/planning/parquet-storage-optimization-plan.md`, possível teste em `tests/`). O piso de verificação pré-commit (ruff check/format, pytest -q) é o mesmo usado para validar qualquer mudança desta rodada.
