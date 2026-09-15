---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-wvzu11-reading-claude-md"
run_id: "2026-09-15-exciting-mccarthy-wvzu11"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "CausaGanha arquiva comunicações judiciais (DJEN) no Internet Archive e serve um dashboard público: backend Python (src/causaganha, src/djen_backup), frontend Astro 7 + Svelte 5 (web/). Regras centrais: sync-manifest.parquet no IA é a fonte única de verdade; djen_raw é sempre o código HTTP bruto, nunca um veredito -- 200 com corpo 'Sem comunicações' é absent; 403 nunca é absent. Upload IA usa httpx (nunca boto3), lock por item + token bucket em archive.py. Fronteira CSS: Panda via preset cobogo é o único sistema; index.css é ponte só para 3 ilhas Svelte legadas. Estilo: ruff estrito, sem except Exception cego fora do bulkhead ADR-0011, TRY300/301/401 aplicados, Python 3.12+. Antes de commitar: ruff check, ruff format --check, pytest -q. CLAUDE.md não menciona segmenter/OPF nem governança de dataset -- essa documentação vive em docs/rfc/0012 e docs/adr/0010 (ver reading-okf). Nada mudou desde a última leitura (yz281l, mesma manhã): nenhuma regra bloqueia trabalhar em scripts/ ou tests/segmenter_dataset/."
---

# Leitura de CLAUDE.md

Leitura integral nesta rodada. Idêntico ao lido em rodadas anteriores do mesmo dia. Relevante para o trabalho desta rodada: nenhuma regra impede um script de diagnóstico read-only em `scripts/segmenter_governance_status.py` nem testes em `tests/segmenter_dataset/`; o piso de verificação pré-commit (`ruff check`, `ruff format --check`, `pytest -q`) é o mesmo usado para validar a mudança.
