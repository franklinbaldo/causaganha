---
type: AgentCheck
id: "2026-09-05-exciting-mccarthy-fnt3vx-check-import-check-pre-delete"
run_id: "2026-09-05-exciting-mccarthy-fnt3vx"
goal_id: "2026-09-05-exciting-mccarthy-fnt3vx-goal-purge-dead-experiment-imports"
command: "uv run python3 -c \"import importlib; [importlib.import_module(m) for m in ['causaganha.analysis.embedding_service_v2','causaganha.analysis.embedding_models','causaganha.pipeline.embedding_pipeline','causaganha.storage.embedding_storage','causaganha.api.client']]\" (each module imported individually with exceptions caught, before deleting the two files)"
result: "failed"
evidence_id: "2026-09-05-exciting-mccarthy-fnt3vx-evidence-red-broken-imports"
summary: "All 5 modules raised ModuleNotFoundError, confirming the two experiments/archive/ files are genuinely non-executable."
---

# Check: imports quebrados antes da remoção
