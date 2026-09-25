---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-qjwekj-evidence-green-juris-kv-metadata"
run_id: "2026-09-25-exciting-mccarthy-qjwekj"
goal_id: "2026-09-25-exciting-mccarthy-qjwekj-goal-juris-kv-metadata"
kind: "test_green"
reference: "src/tjro_juris/service.py"
summary: "Adicionado JURIS_SCHEMA_VERSION='1.0.0' e _kv_metadata_for_export(item_id) a tjro_juris/service.py; _rows_to_parquet ganhou o kwarg obrigatorio item_id e chama table.replace_schema_metadata(...) antes de pq.write_table; crawl_juris passa item_id=f'{ia_archive.IA_ITEM_PREFIX}-{year_month[:4]}' (reusa a constante publica ja usada por tjro_juris.archive para nomear itens IA, sem duplicar o formato). uv run pytest -q tests/tjro_juris/: 110/110 verde (incluindo os 2 testes novos e o teste existente atualizado). uv run ruff check/format --check sobre os arquivos tocados: limpo. Nenhum outro call site de _rows_to_parquet existia (grep confirmado)."
---

# Evidência GREEN: rodapé de identidade presente e legível em juris

Confirma que cada export mensal de `tjro_juris` agora grava
`causaganha.schema_version`/`causaganha.item_id` no rodapé Parquet,
legível tanto por `pyarrow.parquet.read_schema(...).metadata` quanto por
`parquet_kv_metadata()` (DuckDB) — a mesma função que o lado de leitura
`djen` já usa — sem regressão na suíte `tjro_juris` completa.
