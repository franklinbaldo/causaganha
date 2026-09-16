---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-imy2ed-evidence-batch10-ingested"
run_id: "2026-09-16-exciting-mccarthy-imy2ed"
goal_id: "2026-09-16-exciting-mccarthy-imy2ed-goal-djen-sample-batch10"
kind: "runtime"
reference: "docs/planning/evidence/segmenter-djen-sample-batch10-2026-09-16.json, docs/planning/evidence/segmenter-djen-sample-batch10-candidates.json, docs/planning/evidence/segmenter-djen-sample-batch10-overrides.json"
summary: "Two real, previously-unused DJEN Sentença documents (TJBA/574460089, TJRN/72797727) independently annotated by two subagents, then ingested via scripts/ingest_djen_sample_technique1_batch.py into data/segmenter. TJBA's tagged output had a 21-position NBSP-to-space substitution caught by the verbatim-fidelity check; patched programmatically via an offset-mapping walk from the tag-stripped reconstruction back to positions in the raw tagged text, re-verified byte-identical after the patch. Both documents needed --allowed-unmatched-overrides for a dangling capitulo_merito/custas/honorarios pair. Live segmenter_governance_status.py: document_count 109->111, annotation_count 162->164, val_ceiling/test_ceiling 16/16->17/17. segmenter_category_support.py: preliminar_inicio/fim 21->23. segmenter_semantic_audit.py: zero new findings on either new document."
---

# Evidencia: decimo lote real ingerido

Antes de tocar o store real, cada passo foi validado numa copia
(`/tmp/.../store_dry_run3`) e revertido se necessario -- ver
`evidence-dedup-bug-caught-and-reverted.md` para a primeira tentativa
(candidatos errados) e este arquivo para a segunda (candidatos certos,
ingerida com sucesso no store real `data/segmenter`).
