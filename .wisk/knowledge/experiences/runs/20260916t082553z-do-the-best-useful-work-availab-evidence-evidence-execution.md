---
type: "RunEvidence"
id: "run-evidence/20260916t082553z-do-the-best-useful-work-availab/evidence-execution"
run: "runs/20260916T082553Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "https://github.com/franklinbaldo/causaganha/pull/1549 (commit da05b97)"
summary: "Ingested 3 new real Technique 1 documents (TRF3, TJCE, TJMT) into data/segmenter via scripts/ingest_djen_sample_technique1_batch.py -- document_count 93->96 (scripts/segmenter_governance_status.py), preliminar category support 15->16 (scripts/segmenter_category_support.py). Caught and fixed a structural XML-nesting defect in TJCE's subagent-produced annotation (verified via independent verbatim-fidelity re-check, not just trusting the subagent's self-report), supplied allowed-unmatched overrides for 3 dangling start/end pairs the auto-excuse heuristic didn't cover, and discovered+excluded a byte-identical duplicate candidate (TJPB) that would have landed a redundant annotation on an already-ingested batch-2 document. tests/segmenter_dataset/ (373 collected) and the full repo suite both exit 0; ruff clean. Pushed to PR #1549."
goal: "run-goals/20260916t082553z-do-the-best-useful-work-availab/goal-task-advance"
---

# RunEvidence
