---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-qjwekj-evidence-red-juris-kv-metadata"
run_id: "2026-09-25-exciting-mccarthy-qjwekj"
goal_id: "2026-09-25-exciting-mccarthy-qjwekj-goal-juris-kv-metadata"
kind: "test_red"
reference: "tests/tjro_juris/test_juris_service.py"
summary: "2 testes novos escritos primeiro contra a API alvo (JURIS_SCHEMA_VERSION e o kwarg item_id de _rows_to_parquet, ambos ainda inexistentes), mais a chamada existente atualizada para passar item_id (que tambem falha antes da mudanca). uv run pytest -q tests/tjro_juris/test_juris_service.py antes da mudanca de producao: ImportError ('cannot import name JURIS_SCHEMA_VERSION from tjro_juris.service') interrompe a colecao do modulo inteiro -- RED confirmado e isolado a este arquivo (nenhum outro modulo de teste referencia esses simbolos)."
---

# Evidência RED: KV_METADATA ausente nos exports juris

Confirma que, antes da mudança de produção, `tjro_juris.service` não
expõe `JURIS_SCHEMA_VERSION` nem aceita um `item_id` em
`_rows_to_parquet` — a coleta do módulo de teste falha com
`ImportError` ao tentar importar o símbolo alvo.
