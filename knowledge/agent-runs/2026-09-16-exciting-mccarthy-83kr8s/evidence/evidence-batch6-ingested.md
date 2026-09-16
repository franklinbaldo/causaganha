---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-83kr8s-evidence-batch6-ingested"
run_id: "2026-09-16-exciting-mccarthy-83kr8s"
goal_id: "2026-09-16-exciting-mccarthy-83kr8s-goal-djen-sample-batch6"
kind: "runtime"
reference: "docs/planning/evidence/segmenter-djen-sample-batch6-2026-09-16.json, docs/planning/evidence/segmenter-djen-sample-batch6-overrides.json, PYTHONPATH=. uv run python scripts/ingest_djen_sample_technique1_batch.py (live run), uv run python scripts/segmenter_governance_status.py (before/after)"
summary: "Ingested 8 new real Sentenca documents via scripts/ingest_djen_sample_technique1_batch.py: TRF5, TJMT, TJRR, TJPA, TRF3, TJRJ, TJPB, TJES -- all already-represented tribunals (no brand-new tribunal this round, per la7bsl's exhausted-diversity finding). document_count 93->101, annotation_count 142->150, val_ceiling/test_ceiling 14->15. 2/8 candidates (TJRJ, TJPB) passed mechanical validation on the first pass; 6/8 needed a manually reviewed --allowed-unmatched-overrides declaration for dangling relatorio/capitulo_merito/custas/honorarios pairs, all confirmed by direct inspection of the raw tagged text to be the same two known risk-class-1 shapes from prior rounds (Juizado Especial 'relatorio dispensado' with no closing cue; short custas/honorarios clauses with no separate closing phrase) -- see decision-accept-dangling-pairs-as-overrides. No changes to production code (scripts/ingest_djen_sample_technique1_batch.py and its test suite reused as-is, invoked with PYTHONPATH=. since it imports scripts as a package). segmenter_semantic_audit.py's 7 findings are all on pre-existing document ids unrelated to this batch (confirmed by id cross-check) -- zero new findings from the 8 ingested documents."
---

# Evidencia: lote 6 ingerido

Antes: `document_count=93`, `val_ceiling=14`, `test_ceiling=14`.
Depois: `document_count=101`, `val_ceiling=15`, `test_ceiling=15`.
8/8 candidatos selecionados foram ingeridos (2 direto, 6 apos declarar
overrides revisados de pares nao casados). Ver
`docs/planning/evidence/segmenter-djen-sample-batch6-2026-09-16.json`
para os numeros completos.
