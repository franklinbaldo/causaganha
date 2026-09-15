---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-rt6d4o-reading-claude-md"
run_id: "2026-09-15-exciting-mccarthy-rt6d4o"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "CausaGanha arquiva comunicações judiciais (DJEN) no Internet Archive e serve um dashboard público: backend Python (src/causaganha, src/djen_backup), frontend Astro 7 + Svelte 5 (web/). sync-manifest.parquet no IA é fonte única de verdade para o sync engine; djen_raw é sempre o código HTTP bruto (200/404/400/403/timeout/network), nunca um veredito de disponibilidade -- 200 com corpo 'Sem comunicações' é absent. Fronteira CSS: Panda via preset cobogo é o único sistema de design; index.css é ponte de compatibilidade só para 3 ilhas Svelte legadas (ProcessoLookup, PublicationSearch, SavedConsultations). Estilo: ruff estrito, sem except Exception cego fora do bulkhead do ADR-0011, TRY300/301/401 aplicados, Python 3.12+ com `from __future__ import annotations`. Antes de commitar: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`. Nada neste arquivo bloqueia trabalho em web/src/lib/processoCnj.ts (leitura DuckDB-WASM client-side) nem exige mudança nas regras de djen_raw/CSS para essa área. CLAUDE.md não menciona Wisk nem AgentRun -- essa governança de mecanismo de rodada vive só em .claude/hourly-loop.md (ver reading-okf)."
---

# Leitura de CLAUDE.md

Leitura integral nesta rodada. Confirma que o trabalho cogitado (processoCnj.ts, contrato de leitura DuckDB-WASM) não colide com nenhuma regra de correção do djen_raw/sync-manifest (área não tocada) nem com a fronteira Panda/CSS (processoCnj.ts é lógica pura + orquestração SQL, sem estilo). O piso de verificação pré-commit (`ruff check`, `ruff format --check`, `pytest -q`) mais a suíte web (`npx vitest run`, `npm run lint`) seguem sendo o gate desta rodada.
