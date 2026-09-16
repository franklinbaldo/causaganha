---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-0iuk22-evidence-real-batch-ingested"
run_id: "2026-09-16-exciting-mccarthy-0iuk22"
goal_id: "2026-09-16-exciting-mccarthy-0iuk22-goal-djen-sample-corpus-growth"
kind: "runtime"
reference: "docs/planning/evidence/segmenter-djen-sample-batch1-2026-09-16.json, data/segmenter/documents/ (7 new *.xml files), scripts/ingest_djen_sample_technique1_batch.py"
summary: "Selected 7 real, unused, already-fetched candidate documents from data/segmenter_samples/*.jsonl (TJMT, TJPA, TRF3, TJCE, TJES sentencas + TRF5, TJSE acordaos -- all rare-category cue hits: preliminar/honorarios/custas/voto/acordao_decisorio). Spawned one subagent per document with the canonical Technique 1 prompt (data/segmenter_splits/technique1_annotation_prompt.md), each independently reading the document, tagging it inline, and self-verifying verbatim fidelity before writing its output. Ran scripts/ingest_djen_sample_technique1_batch.py against the batch: all 7 initially failed mechanical validation (dangling relatorio/custas/honorarios/capitulo_merito pairs with no closing cue in source text, not positionally last so not auto-excused by _detect_allowed_unmatched) -- reviewed each skip reason against the annotating subagent's own stated rationale and supplied a manually reviewed --allowed-unmatched-overrides JSON (same mechanism annotate_second_independent.py already exposes) for the genuinely-no-closing-cue cases. Re-ran: 7/7 ingested. scripts/segmenter_governance_status.py before/after: document_count 61->68, train_eligible_count 61->68, val_ceiling_at_full_adjudication 9->10, test_ceiling_at_full_adjudication 9->10. store.list_documents() confirms source.tribunal now spans {TJRO: 61, TJMT: 1, TJPA: 1, TRF3: 1, TJCE: 1, TJES: 1, TRF5: 1, TJSE: 1} and source.system gained djen_sample_technique1: 7 -- the first non-TJRO documents ever in the store."
---

# Evidencia: primeiro lote real multi-tribunal ingerido no store

```
$ uv run python scripts/segmenter_governance_status.py --store data/segmenter
# antes
document_count=61 val_ceiling_at_full_adjudication=9 test_ceiling_at_full_adjudication=9
# depois (7 documentos ingeridos)
document_count=68 val_ceiling_at_full_adjudication=10 test_ceiling_at_full_adjudication=10
```

```
$ uv run python -m scripts.ingest_djen_sample_technique1_batch \
    --candidates .../candidates.json --tagged-dir .../tagged \
    --output data/segmenter --completed-at 2026-09-16T01:40:00Z \
    --allowed-unmatched-overrides .../allowed_unmatched_overrides.json
Ingested 7 document(s): ...
```

Tribunais novos no store: TJMT, TJPA, TRF3, TJCE, TJES, TRF5, TJSE (todos
ausentes ate esta rodada -- os 61 documentos anteriores eram 100% TJRO).
