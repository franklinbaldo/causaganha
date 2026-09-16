---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-83kr8s-evidence-no-new-semantic-findings"
run_id: "2026-09-16-exciting-mccarthy-83kr8s"
goal_id: "2026-09-16-exciting-mccarthy-83kr8s-goal-djen-sample-batch6"
kind: "test_green"
reference: "uv run python scripts/segmenter_semantic_audit.py (live run, post-ingestion)"
summary: "segmenter_semantic_audit.py reports 7 findings after this round's ingestion, all on document ids (doc_3cffd796..., doc_b0c36490..., doc_b8a4a405..., doc_c502b14f..., doc_c7724144..., doc_d61aecbf..., doc_f985597a...) that do not match any of this round's 8 newly ingested document ids (doc_f3e10e0e..., doc_4e69e1b7..., doc_4c9d2f60..., doc_4978f34f..., doc_003c99b9..., doc_a384e2be..., doc_1f1b8dde..., doc_64af64e7...) -- confirmed by direct id cross-check, not by finding count alone. Zero new semantic findings introduced by this batch."
---

# Evidencia: sem novos achados semanticos

`scripts/segmenter_semantic_audit.py` continua com os mesmos 7 achados
pre-existentes de rodadas anteriores (ids de documentos que nao
correspondem a nenhum dos 8 documentos ingeridos nesta rodada,
confirmado por comparacao direta de ids). Nenhum achado novo introduzido
pelo lote 6.
