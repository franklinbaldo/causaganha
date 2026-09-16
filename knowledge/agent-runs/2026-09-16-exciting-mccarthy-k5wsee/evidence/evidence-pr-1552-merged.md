---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-k5wsee-evidence-pr-1552-merged"
run_id: "2026-09-16-exciting-mccarthy-k5wsee"
goal_id: "2026-09-16-exciting-mccarthy-k5wsee-goal-resume-pr-1552"
kind: "pr"
reference: "https://github.com/franklinbaldo/causaganha/pull/1552"
summary: "PR #1552 mesclada (squash) como c9c09b11e36c5af23e91b9ce89191d39ec8273d6 em main, com titulo corrigido para 'ingest eighth real multi-tribunal batch' (o titulo original dizia 'sixth', desatualizado pela corrida com os lotes 6 e 7 mesclados por outras sessoes enquanto esta PR ficava parada). Resultado: document_count 101(isolado)->109(ao vivo pos-reconciliacao), val_ceiling/test_ceiling 14->16, annotation_count->162, review_count=31. Confirmado apos o merge via git fetch origin main (c9c09b1) e scripts/segmenter_governance_status.py."
---

# Evidencia: PR #1552 mesclada

expectedHeadSha=224f1d0b904d1ba0f96b3cdfd07dcfba3fc43dad conferido antes
do merge (squash) para evitar mesclar um estado inesperado caso a sessao
83kr8s ainda estivesse ativa e pushasse algo entre minha checagem e o
merge -- nao pushou nada mais, o merge foi limpo.
