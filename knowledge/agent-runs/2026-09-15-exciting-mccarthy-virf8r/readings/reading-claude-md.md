---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-virf8r-reading-claude-md"
run_id: "2026-09-15-exciting-mccarthy-virf8r"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "CausaGanha arquiva comunicações judiciais (DJEN) no Internet Archive e serve um dashboard público: backend Python (src/causaganha, src/djen_backup), frontend Astro 7 + Svelte 5 (web/). Regras centrais: sync-manifest.parquet no IA é a fonte única de verdade; djen_raw é sempre o código HTTP bruto, nunca um veredito -- 200 com corpo 'Sem comunicações' é absent; 403 nunca é absent. Upload IA usa httpx (nunca boto3), lock por item + token bucket em archive.py. Fronteira CSS: Panda via preset cobogo é o único sistema; index.css é ponte só para 3 ilhas Svelte legadas. Estilo: ruff estrito, sem except Exception cego fora do bulkhead ADR-0011, TRY300/301/401 aplicados, Python 3.12+. Antes de commitar: ruff check, ruff format --check, pytest -q. CLAUDE.md não menciona segmenter/OPF nem governança de dataset -- essa documentação vive em docs/rfc/0012 e docs/adr/0010. Nenhuma regra deste arquivo impede trabalho em src/segmenter_dataset/, scripts/ ou tests/segmenter_dataset/."
---

# Leitura de CLAUDE.md

Leitura integral nesta rodada. Conteúdo idêntico ao lido por todas as rodadas do dia anterior (nenhuma mudança desde a última leitura, 5crg57). Relevante para o trabalho desta rodada: o piso de verificação pré-commit (`ruff check`, `ruff format --check`, `uv run pytest -q`) é o mesmo que valida qualquer mudança em `src/segmenter_dataset/`/`scripts/`; nenhuma seção do arquivo trata do segmentador/OPF, então a governança de qualidade de dados desse domínio vive inteiramente em `docs/rfc/0012-segmenter-dataset-confiavel-baseline.md`.
