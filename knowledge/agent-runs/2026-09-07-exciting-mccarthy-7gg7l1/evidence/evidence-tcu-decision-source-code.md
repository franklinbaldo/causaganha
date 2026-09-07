---
type: AgentEvidence
id: "2026-09-07-exciting-mccarthy-7gg7l1-evidence-tcu-decision-source-code"
run_id: "2026-09-07-exciting-mccarthy-7gg7l1"
goal_id: "2026-09-07-exciting-mccarthy-7gg7l1-goal-reconcile-backlog"
kind: "other"
reference: "src/causaganha/decisoes/planner.py:17 (DecisionSource = Literal['todas','juris','stj','tcu']); src/causaganha_mcp/knowledge.py (PipelineMetadata, load_pipeline_metadata); tests/causaganha_mcp/test_okf_pipeline_catalog.py:13-18 (_EXPECTED exact-set of 4 pipelines)"
summary: "Confirms the factual basis for decision-tcu-fonte-gap: DecisionSource already treats 'tcu' as a first-class content source at the code level, while the OKF Fonte/Pipeline relation and its exact-set contract test are scoped to exactly 4 continuous sync pipelines (djen, tjro_juris, stj_acordaos, datajud), none of which is 'tcu'. grep across src/causaganha/decisoes/{search,published}.py found no existing mapping table between DecisionSource's short codes ('juris','stj','tcu') and Fonte.nome's pipeline-module names ('tjro_juris','stj_acordaos') for the two sources that already overlap."
---

# Evidência: leitura do código de `DecisionSource` e do catálogo de pipelines

`DecisionSource` já inclui `'tcu'`; o catálogo `Fonte`/`Pipeline` (e seu teste de conjunto exato) cobre só os 4 motores de sincronização contínuos. Não existe tabela de alias entre os dois eixos.
