---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-qn6gvy-evidence-live-kv-metadata-probe"
run_id: "2026-09-25-exciting-mccarthy-qn6gvy"
kind: "runtime"
reference: "uv run python -c \"...parquet_kv_metadata(...)\" contra https://archive.org/download/djen-tjro-2026/comunicacoes.parquet"
summary: "uv run python -c \"...parquet_kv_metadata('https://archive.org/download/djen-tjro-2026/comunicacoes.parquet')...\" contra o Internet Archive real (não um mock) retornou as 4 entradas de KV_METADATA que schema_registry.kv_metadata_for_export escreve: causaganha.schema_version=3.0.0, causaganha.item_id=djen-tjro-2026, causaganha.layout=cnj-text-sorted-v1, causaganha.cnj_normalization=valid-20-digits-v1. Confirma ao vivo (a) que o rodapé existe de fato nos artefatos publicados, não só na intenção do exportador, e (b) que a leitura via httpfs completa em segundos (leitura de rodapé, não do arquivo de ~766KB inteiro) -- a base técnica da decisão de usar parquet_kv_metadata() em vez de hash de conteúdo completo."
---

# Evidência: prova ao vivo de KV_METADATA contra archive.org real
