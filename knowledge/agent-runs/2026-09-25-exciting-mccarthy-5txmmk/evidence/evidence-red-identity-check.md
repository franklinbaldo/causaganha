---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-5txmmk-evidence-red-identity-check"
run_id: "2026-09-25-exciting-mccarthy-5txmmk"
goal_id: "2026-09-25-exciting-mccarthy-5txmmk-goal-reconcile-identity-check"
kind: "test_red"
reference: "tests/test_reconcile_processos.py::TestArtifactIdentityVerification"
summary: "4 testes novos escritos primeiro contra a API alvo (fetch_juris_from_ia/fetch_datajud_from_ia ainda sem verificacao de identidade). uv run pytest -q tests/test_reconcile_processos.py::TestArtifactIdentityVerification antes da mudanca de producao: 3/4 falham com 'Failed: DID NOT RAISE SourceDataError' -- test_juris_shard_without_identity_metadata_is_rejected, test_juris_shard_with_mismatched_item_id_is_rejected, test_datajud_capa_with_mismatched_item_id_is_rejected. O 4o (test_valid_identity_metadata_is_accepted, o caso feliz de linha de base) ja passa nesta fase, como esperado -- nao ha nada para rejeitar antes da checagem existir. RED confirmado e isolado a esta classe."
---

# Evidência RED: fetch remoto de JURIS/DataJud aceita conteúdo sem verificar identidade

Antes da mudança de produção, `fetch_juris_from_ia`/`fetch_datajud_from_ia`
aceitam qualquer arquivo estruturalmente válido como Parquet, mesmo sem
`causaganha.item_id`/`causaganha.schema_version` no rodapé, ou com um
`item_id` que diverge do item do qual foi baixado — 3 dos 4 testes novos
falham com `DID NOT RAISE SourceDataError`, confirmando a lacuna que o
item (3) de #1652/TM-16 aponta.
