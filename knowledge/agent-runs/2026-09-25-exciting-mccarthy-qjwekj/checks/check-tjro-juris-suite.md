---
type: AgentCheck
id: "2026-09-25-exciting-mccarthy-qjwekj-check-tjro-juris-suite"
run_id: "2026-09-25-exciting-mccarthy-qjwekj"
goal_id: "2026-09-25-exciting-mccarthy-qjwekj-goal-juris-kv-metadata"
command: "uv run pytest -q tests/tjro_juris/"
result: "passed"
evidence_id: "2026-09-25-exciting-mccarthy-qjwekj-evidence-green-juris-kv-metadata"
summary: "110/110 testes verdes apos a mudanca, incluindo os 2 testes novos de KV_METADATA e o teste existente atualizado para passar item_id -- nenhuma regressao no restante do pacote tjro_juris (crawler, dedup, manifest, archive, main)."
---

# Check: suíte tjro_juris completa

`tests/tjro_juris/` completa passou (110 testes) após a mudança em
`_rows_to_parquet`, incluindo os 2 testes novos de `KV_METADATA` e o
teste existente que foi atualizado para passar `item_id`.
