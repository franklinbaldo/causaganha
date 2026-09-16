---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-la7bsl-evidence-batch5-ingested"
run_id: "2026-09-16-exciting-mccarthy-la7bsl"
kind: "runtime_behavior"
reference: "docs/planning/evidence/segmenter-djen-sample-batch5-2026-09-16.json, docs/planning/evidence/segmenter-djen-sample-batch5-overrides.json, uv run python -m scripts.ingest_djen_sample_technique1_batch (live run), uv run python scripts/segmenter_governance_status.py (before/after)"
summary: "Ingested 7 new real Acordao documents via scripts/ingest_djen_sample_technique1_batch.py: 4 TJMS (a new, 25th tribunal), 2 TJPA, 1 TJPI. document_count 86->93, annotation_count 135->142, val_ceiling/test_ceiling 13->14. One manual --allowed-unmatched-overrides entry needed (TJPA 581175574's unmatched 'custas' pair, confirmed genuinely closing-cue-free). All 4 TJMS candidates required normalizing texto_limpo's CRLF line endings to LF before ingestion, since XML's mandatory end-of-line normalization (sec 2.11) makes CRLF unrecoverable through the existing tag-and-reconstruct mechanism regardless of annotation quality -- documented as decision-normalize-crlf-before-candidate."
---

# Evidencia: lote 5 ingerido

Antes: `document_count=86`, `val_ceiling=13`, `test_ceiling=13`.
Depois: `document_count=93`, `val_ceiling=14`, `test_ceiling=14`.
TJMS entra como 25o tribunal no store. 7/7 candidatos selecionados
foram ingeridos (6 direto, 1 apos declarar override de par nao
casado). Ver `docs/planning/evidence/segmenter-djen-sample-batch5-2026-09-16.json`
para os numeros completos e achados.
