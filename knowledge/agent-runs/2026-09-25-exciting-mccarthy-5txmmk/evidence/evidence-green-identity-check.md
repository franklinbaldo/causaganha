---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-5txmmk-evidence-green-identity-check"
run_id: "2026-09-25-exciting-mccarthy-5txmmk"
goal_id: "2026-09-25-exciting-mccarthy-5txmmk-goal-reconcile-identity-check"
kind: "test_green"
reference: "scripts/reconcile_processos.py::_verify_artifact_identity"
summary: "Apos adicionar _kv_metadata/_verify_artifact_identity a scripts/reconcile_processos.py e chama-los em fetch_juris_from_ia/fetch_datajud_from_ia logo apos _fetch_cached: uv run pytest -q tests/test_reconcile_processos.py::TestArtifactIdentityVerification -- 4/4 verdes (os 3 casos de rejeicao viram SourceDataError esperado, o caso feliz continua aceito). uv run pytest -q tests/test_reconcile_processos.py -- 35/35 verdes, incluindo todos os testes pre-existentes de fluxo feliz apos _juris_parquet ganhar o parametro item= (que grava o mesmo KV_METADATA causaganha.schema_version/causaganha.item_id que tjro_juris.service._rows_to_parquet grava em producao) e os 5 call sites remotos passarem a usa-lo -- nenhuma regressao. datajud ja gravava o rodape correto via write_capa_parquet (producao real), entao nenhuma fixture datajud precisou de mudanca."
---

# Evidência GREEN: identidade verificada no fetch remoto de JURIS/DataJud

`_verify_artifact_identity` (via `_kv_metadata`, leitura local de
`parquet_kv_metadata`) agora roda logo após cada download em
`fetch_juris_from_ia`/`fetch_datajud_from_ia`, rejeitando (com
`SourceDataError`, mesmo tipo já usado para parquet corrompido) qualquer
arquivo sem o rodapé de identidade `causaganha.*` ou com `item_id`
divergente do item do qual foi baixado. Suite completa do arquivo:
35/35 verde, sem regressão nos testes de fluxo feliz pré-existentes.
