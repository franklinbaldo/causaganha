---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-imy2ed-decision-fix-candidate-dedup-hash-space"
run_id: "2026-09-16-exciting-mccarthy-imy2ed"
goal_id: "2026-09-16-exciting-mccarthy-imy2ed-goal-djen-sample-batch10"
question: "This round's first candidate selection (TJRN/72798564, TJBA/574460090) excluded already-used candidates by comparing each pool record's raw DJEN sha256 (info.sha256) against SegmenterDatasetStore documents' source.source_hash field. Ingesting them produced zero new DocumentRecords (write_document no-op'd: both source_uris already existed) and two redundant same-annotator-id AnnotationRecords on already-annotated documents (annotator id 'llm_technique1:djen_sample_batch1' is a fixed constant, so a second annotation under it has no independent-adjudication value per RFC 0012 Sec 9). Revert and re-select properly, or keep the two extra same-annotator annotations since they're technically valid AnnotationRecords?"
choice: "Reverted both annotation files (git status confirmed data/segmenter was clean again after removal) and re-ran candidate selection using segmenter_dataset.dedup.content_hash(text) over the document's own .text field plus a direct (tribunal, id_documento) match against existing documents' source_uri -- the same identity fields build_document_id actually hashes on (segmenter_dataset/ids.py's document_id()). This surfaced two different, genuinely new candidates (TJBA/574460089, TJRN/72797727)."
rationale: "store.source_hash is content_hash(cleaned_text) -- a locally-normalized SHA-256 the store computes itself -- while the pool's info.sha256 is DJEN's own hash of the raw fetched artifact upstream. The two hash spaces are unrelated; comparing across them can never detect a true duplicate and happened to let two already-ingested (tribunal, id_documento) pairs through. The document_id formula (segmenter_dataset/ids.py) is keyed on (source_system, source_uri, source_hash=content_hash(text)), so the only correct way to check 'already ingested' before spending a subagent call is to recompute content_hash(text) with the same function the store uses, and/or match (tribunal, id_documento) against existing source_uri strings directly -- not to trust an externally-sourced hash field that was never guaranteed to align with the store's own identity scheme. Since write_document() is deliberately idempotent (RFC 0012 Sec 3.1 ImmutabilityError guard) rather than silently erroring, this mistake was caught by inspecting git status (no new document file appeared) instead of trusting the script's own 'Ingested N document(s)' success message, which reports on annotation writes succeeding, not on whether a document was newly created vs already present."
---

# Decisao: corrigir o espaco de hash usado para deduplicar candidatos

Ver `evidence/evidence-dedup-bug-caught-and-reverted.md` para a evidencia
completa (comandos, saidas, git status antes/depois). Nenhum documento ou
anotacao invalida permaneceu no store real (`data/segmenter`) apos esta
correcao -- a reversao foi confirmada por `git status --short data/segmenter`
retornando vazio antes de qualquer novo trabalho comecar.
