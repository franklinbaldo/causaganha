---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-cdee4f-reading-claude-md"
run_id: "2026-09-15-exciting-mccarthy-cdee4f"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "CausaGanha arquiva comunicações judiciais (DJEN) no Internet Archive e serve um dashboard público: backend Python (src/causaganha, src/djen_backup), frontend Astro 7 + Svelte 5 (web/). sync-manifest.parquet no IA é fonte única de verdade para o sync engine; djen_raw é sempre o código HTTP bruto, nunca um veredito de disponibilidade. Estilo: ruff estrito, sem except Exception cego fora do bulkhead do ADR-0011, TRY300/301/401 aplicados, Python 3.12+ com `from __future__ import annotations`. Antes de commitar: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`. Nada neste arquivo bloqueia trabalho em scripts/reconcile_processos.py (script Python de reconciliação de fontes, sem UI) nem exige mudança de regra de djen_raw/CSS para essa área -- o arquivo só orienta o padrão já usado por exporter.py (COPY ... FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE explícito) como precedente direto para o mesmo tipo de mudança em reconcile_processos.py."
---

# Leitura de CLAUDE.md

Leitura integral nesta rodada. Confirma que o trabalho cogitado (explicitar ROW_GROUP_SIZE e ordem física na escrita de `indice_processual.parquet` em `scripts/reconcile_processos.py`) segue exatamente o precedente já estabelecido em `src/causaganha/consolidate/exporter.py` (issue #1469, critério "Usar ZSTD e ROW_GROUP_SIZE 122880"), sem colidir com nenhuma regra de correção do djen_raw/sync-manifest (área não tocada) nem com a fronteira Panda/CSS (script Python puro). O piso de verificação pré-commit (`ruff check`, `ruff format --check`, `pytest -q`) segue sendo o gate desta rodada.
