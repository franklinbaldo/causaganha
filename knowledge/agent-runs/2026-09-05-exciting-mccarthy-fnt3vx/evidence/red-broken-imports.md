---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-fnt3vx-evidence-red-broken-imports"
run_id: "2026-09-05-exciting-mccarthy-fnt3vx"
goal_id: "2026-09-05-exciting-mccarthy-fnt3vx-goal-purge-dead-experiment-imports"
kind: "runtime"
reference: "uv run python3 -c \"import causaganha.analysis.embedding_service_v2\" (and 4 sibling imports), run against experiments/archive/test_all_improvements.py and experiments/archive/test_djen_api.py's exact import lines, before deletion"
summary: "5 of the 6 non-stdlib imports across the two files raise ModuleNotFoundError: causaganha.analysis.embedding_service_v2, causaganha.analysis.embedding_models, causaganha.pipeline.embedding_pipeline, causaganha.storage.embedding_storage (all from test_all_improvements.py) and causaganha.api.client (from test_djen_api.py). Confirms #924's claim that these files reference genuinely removed infrastructure, not just an unverified model assertion."
---

# Evidência RED — imports quebrados em experiments/archive/

Antes de remover os arquivos, cada import não-stdlib foi testado individualmente contra o pacote instalado. Cinco de seis falharam com `ModuleNotFoundError`, confirmando que os módulos foram de fato removidos do código-fonte, não apenas renomeados ou movidos.
