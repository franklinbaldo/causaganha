---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-bc9ae6-reading-claude-md"
run_id: "2026-09-15-exciting-mccarthy-bc9ae6"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "CausaGanha arquiva comunicações judiciais (DJEN) no Internet Archive e serve um dashboard público: backend Python (src/causaganha, src/djen_backup), frontend Astro 7 + Svelte 5 (web/). Regras centrais: sync-manifest.parquet no IA é a fonte única de verdade; djen_raw é sempre o código HTTP bruto, nunca um veredito -- 200 com corpo 'Sem comunicações' é absent, não available; 403 nunca é absent (rate limit). Upload IA usa httpx (nunca boto3), lock por item + token bucket em archive.py. Fronteira CSS: Panda via preset cobogo é o único sistema; index.css é ponte de compatibilidade só para 3 ilhas Svelte legadas. Estilo: ruff estrito, sem except Exception cego fora do bulkhead ADR-0011, TRY300/301/401 aplicados, Python 3.12+ com `from __future__ import annotations`. Antes de commitar: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`. Nenhuma regra nova relevante ao segmenter/RFC 0012 (o trabalho escolhido nesta rodada vive em src/segmenter_dataset e data/segmenter, fora do escopo direto de djen_backup/exporter, mas ainda sujeito ao mesmo piso de lint/teste)."
---

# Leitura de CLAUDE.md

Leitura integral nesta rodada. Sem mudanças relevantes desde a última leitura registrada (yz281l, mesmo dia): contratos de djen_raw/djen_status, fronteira Panda/CSS e regras de estilo seguem idênticos. Nenhuma regra bloqueia ou altera o trabalho escolhido nesta rodada (scaling de ReviewRecords do segmenter, ver goal) — o piso de verificação (`ruff check`, `ruff format --check`, `pytest -q`) é o mesmo aplicado a qualquer mudança no repositório, incluindo `src/segmenter_dataset/` e `scripts/annotate_second_independent.py`/`scripts/adjudicate_segmenter_review.py`.
