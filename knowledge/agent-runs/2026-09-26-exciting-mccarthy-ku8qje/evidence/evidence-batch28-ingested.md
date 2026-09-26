---
type: AgentEvidence
id: "2026-09-26-exciting-mccarthy-ku8qje-evidence-batch28-ingested"
run_id: "2026-09-26-exciting-mccarthy-ku8qje"
goal_id: "2026-09-26-exciting-mccarthy-ku8qje-goal-segmenter-batch28"
kind: "diff"
reference: "data/segmenter/documents/doc_c44b9ef9667a2354fdd2499d83474c5f.xml, data/segmenter/documents/doc_0ab27b0e0c880d3eadb7546bce750c79.xml, data/segmenter/annotations/doc_c44b9ef9667a2354fdd2499d83474c5f/, data/segmenter/annotations/doc_0ab27b0e0c880d3eadb7546bce750c79/"
summary: "`scripts/ingest_djen_sample_technique1_batch.py` ingeriu os 2 documentos do Lote 28 (TJPB/578828501 -> doc_c44b9ef9667a2354fdd2499d83474c5f, hash 9b4452b6...; TJMT/74433596 -> doc_0ab27b0e0c880d3eadb7546bce750c79, hash a3716fe5...), train-only, com overrides declarados para 3 pares sem cue de fechamento (relatorio em ambos; custas+honorarios em TJMT). Ambos verificados independentemente ANTES da ingestao via `segmenter_dataset.store._text_element_to_labels` real (fidelidade verbatim byte-a-byte confirmada) e `segmenter_dataset.mechanical.validate_record` (zero problemas mecanicos com os overrides declarados). `git status --short data/segmenter` confirmou exatamente 2 novos `documents/*.xml` e 2 novos `annotations/<id>/`, sem write no-op ou efeito colateral em outro documento. `scripts/segmenter_governance_status.py` pos-ingestao: document_count 195->197, annotation_count 253->255, val_ceiling_at_full_adjudication/test_ceiling_at_full_adjudication 29/29->30/30, corpus_scale_blocks_floor True->False. `scripts/segmenter_semantic_audit.py` pos-ingestao: zero achados novos (os mesmos 7 doc_ids `_collapsed` da allowlist, nenhum dos dois documentos novos aparece)."
---

# Evidência: Lote 28 ingerido (GREEN)

2 documentos novos train-only ingeridos, verificados mecanicamente e por
fidelidade verbatim antes da escrita. `document_count` 195->197 liberou
o teto real de val/test de RFC 0012 (29/29 -> 30/30,
`corpus_scale_blocks_floor` agora `False`). Nenhum achado novo no
audit semantico.
