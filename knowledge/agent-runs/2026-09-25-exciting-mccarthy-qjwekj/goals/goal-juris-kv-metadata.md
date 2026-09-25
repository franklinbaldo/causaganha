---
type: AgentGoal
id: "2026-09-25-exciting-mccarthy-qjwekj-goal-juris-kv-metadata"
run_id: "2026-09-25-exciting-mccarthy-qjwekj"
goal: "Embutir causaganha.schema_version/causaganha.item_id no rodape KV_METADATA de cada Parquet mensal exportado por tjro_juris.service._rows_to_parquet, fechando o lado de escrita do gap documentado em TM-04 (docs/SECURITY_THREAT_MODEL.md): 'juris/stj/datajud nao emitem esse KV_METADATA hoje'."
rationale: "TM-04 exige que cada transicao de dado preserve identidade verificavel (generation id, schema fingerprint). djen ja grava essa identidade via causaganha.consolidate.schema_registry.kv_metadata_for_export, e o lado de leitura (service._validar_metadata_djen) a usa para descartar artefatos cujo rodape Parquet diverge da URL do indice que os nomeia. juris e stj nao emitiam nada equivalente -- stj_acordaos nao tem nenhum pipeline write_parquet/to_parquet sob controle deste repo (fora de escopo), mas tjro_juris.service._rows_to_parquet escreve parquet via pyarrow a cada janela mensal e pode ganhar a mesma identidade sem tocar o lado de leitura (evitando sobreposicao com a PR #1646, de outra sessao, que toca o mesmo pacote tjro_juris mas em manifest.py)."
success_signal: "Testes novos em tests/tjro_juris/test_juris_service.py provam RED->GREEN: (1) o rodape Parquet escrito por _rows_to_parquet contem causaganha.schema_version==JURIS_SCHEMA_VERSION e causaganha.item_id==<item_id> via pq.read_schema(...).metadata; (2) o mesmo rodape e legivel via DuckDB parquet_kv_metadata(), a mesma funcao que o lado de leitura djen ja usa -- prova que um futuro validador de leitura para juris pode reusar o mecanismo existente sem mudanca de abordagem. Suite tests/tjro_juris/ completa permanece verde (110 testes). uv run ruff check/format --check limpos. docs/SECURITY_THREAT_MODEL.md TM-04 atualizado para registrar o lado de escrita fechado para juris e o lado de leitura como pendencia explicita."
status: "achieved"
---

# Goal: KV_METADATA de identidade nos exports Parquet do juris

Fechar o lado de escrita do gap TM-04 para `tjro_juris`: cada export
mensal passa a declarar sua própria identidade (`schema_version` +
`item_id`) no rodapé Parquet, no mesmo namespace `causaganha.*` já usado
pelos exports djen, tornando possível um futuro validador de leitura
espelhar `causaganha.processos.service._validar_metadata_djen` para
juris sem inventar um mecanismo novo.
