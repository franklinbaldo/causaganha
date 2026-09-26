---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-o3ubcj-reading-okf"
run_id: "2026-09-25-exciting-mccarthy-o3ubcj"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/2026-09-25-exciting-mccarthy-{qn6gvy,r2xele}/run.md + docs/SECURITY_THREAT_MODEL.md (TM-04) + src/causaganha/processos/service.py + web/src/lib/processoCnj.ts"
finding: "r2xele (03:23Z) fechou a metade TypeScript da política de URL de artefato (#1610): ArtifactUrlError/validateArtifactUrl em processoCnj.ts, espelhando service._validate_artifact_url. qn6gvy (10:29Z) fechou a fatia 'schema fingerprint' de TM-04 SÓ do lado Python: service._item_id_da_url/_validar_metadata_djen/_kv_metadata/_validar_metadata_djen_urls, lendo o rodapé KV_METADATA (causaganha.schema_version/item_id) via parquet_kv_metadata() antes de compor read_parquet. O next_move de qn6gvy nomeia explicitamente o gap remanescente: 'portar a mesma checagem de rodapé para o lado TypeScript (web/src/lib/processoCnj.ts), que já seleciona tribunal mas ainda não faz nem a checagem de tribunal nem a de KV_METADATA'. Confirmado por leitura direta de processoCnj.ts linha ~152-155 (comentário dizia literalmente 'A checagem de coerência de proveniência que o lado Python já faz com essa coluna ... é follow-up do lado Web') e por grep: nenhuma menção a tribunal-coerência ou parquet_kv_metadata-para-item_id existia no arquivo antes desta rodada. TM-04 no SECURITY_THREAT_MODEL.md também listava 'as duas checagens do lado Web' como pendente explícito. Este é exatamente o gap tratável, self-contained e TDD-ável identificado por duas rodadas seguidas sem ser fechado -- selecionado como trabalho desta rodada em vez de reabrir o cluster segmenter (#1050), que outras rodadas de hoje já vêm avançando em paralelo."
---

# Leitura: OKF (rodadas recentes + prior art)
