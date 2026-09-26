---
type: AgentEvidence
id: "2026-09-26-exciting-mccarthy-p08457-evidence-reviews-ingested"
run_id: "2026-09-26-exciting-mccarthy-p08457"
goal_id: "2026-09-26-exciting-mccarthy-p08457-goal-1051-test-split-adjudication"
kind: "runtime"
reference: "data/segmenter/reviews/doc_0db5fffa04141a164fb9c48f11bb8c01/rev_e93d83193c8873cea54f9cccec74d847.xml, data/segmenter/reviews/doc_174797b9bfde68303b3e00c43ac291fe/rev_4baa3dfb71c908c8a14b9a41b3fb19b7.xml"
summary: "scripts/adjudicate_segmenter_review.py escreveu 2 ReviewRecords aceitos com sucesso. scripts/segmenter_governance_status.py, rodado ao vivo apos a ingestao, confirma: document_count=197 (inalterado), annotation_count 253->257, review_count 32->34, evaluation_eligible_count 32->34, val_count=30 (inalterado, no teto), test_count 2->4 (o metric alvo desta rodada, exatamente como a simulacao previa havia previsto), meets_rfc_0012_split_floor ainda False (30/4 < 30/30), corpus_scale_blocks_floor ainda False. git status --short data/segmenter confirmou exatamente 2 novos arquivos de anotacao e 2 novos diretorios de review, sem efeito colateral em nenhum outro documento."
---

# Evidencia: 2 ReviewRecords ingeridos, test_count 2->4

`scripts/segmenter_governance_status.py` apos a ingestao:
`review_count` 32->34, `test_count` 2->4 (exatamente como a simulacao
previa havia previsto), `val_count` inalterado em 30 (ja no teto).
`git status --short data/segmenter` confirma exatamente os 4 arquivos
esperados, sem efeito colateral.
