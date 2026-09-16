---
goal: "Grow the real segmenter training corpus (#1050) with a sixth Technique 1 batch: 4 new real, multi-tribunal DJEN Sentenca documents (TRF3, TJCE, TJMT, TJPB -- each currently represented by only 1 document in the store), selected from the pre-mined data/segmenter_samples/*.jsonl pool for hitting the 'preliminar' cue (the corpus's scarcest category at 15 instances, per scripts/segmenter_category_support.py), independently annotated by one subagent per document via the canonical Technique 1 prompt, then ingested via scripts/ingest_djen_sample_technique1_batch.py."
id: "run-goals/20260916t082553z-do-the-best-useful-work-availab/goal-task-advance"
kind: "task-advance"
rationale: "#1050 explicitly asks for more real documents across multiple tribunals/templates, not just adjudicating the existing pool, to clear RFC 0012 Sec5 item4's >=30/>=30 val/test floor (currently ceiling 14/14 at 93 docs). This is the fifth consecutive real batch using this exact mechanism (batches 1-5 already merged, #1547 most recent) and, unlike #1469/#1471/#1472/#1482, requires no Internet Archive or Cloudflare write credentials -- it is fully actionable in this environment."
run: "runs/20260916T082553Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "document_count increases from 93 (verified via scripts/segmenter_governance_status.py / the store's own document count) by the number of candidates that pass mechanical verbatim-fidelity + validate_record checks; a new tests/segmenter_dataset test (or an existing one extended) goes RED against main's current store state and GREEN once the batch is ingested; uv run pytest -q stays green repo-wide."
type: "RunGoal"
---

# RunGoal
