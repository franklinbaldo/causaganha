---
type: AgentEvidence
id: "2026-09-26-exciting-mccarthy-kgxf50-evidence-reviews-ingested"
run_id: "2026-09-26-exciting-mccarthy-kgxf50"
goal_id: "2026-09-26-exciting-mccarthy-kgxf50-goal-1051-test-split-adjudication"
kind: "diff"
reference: "data/segmenter/annotations/{doc_d3de3dfe95769791db33077c54bd3724,doc_4a8e16820fb9c8fa1d808d717d9a34d7,doc_3b0be436ba6753185997c37b2b6b9765}/*.xml + data/segmenter/reviews/{same 3 doc_ids}/*.xml"
summary: "3 new AnnotationRecords (model_family=prompt_subagents:haiku, seeded_with=none) and 3 new accepted ReviewRecords written via scripts/annotate_second_independent.py and scripts/adjudicate_segmenter_review.py. scripts/segmenter_governance_status.py confirms review_count 34->37, test_count 4->7 (val_count unchanged at 30, its ceiling) -- exactly matching the pre-round joint simulation."
---

# Evidence: 3 reviews ingested, governance status moved as simulated

```
$ uv run python scripts/segmenter_governance_status.py --store data/segmenter
{
  "document_count": 197,
  "annotation_count": 260,
  "review_count": 37,
  "train_eligible_count": 197,
  "evaluation_eligible_count": 37,
  "blocked_on_reviews": false,
  "val_count": 30,
  "test_count": 7,
  "val_ceiling_at_full_adjudication": 30,
  "test_ceiling_at_full_adjudication": 30,
  "meets_rfc_0012_split_floor": false,
  "corpus_scale_blocks_floor": false
}
```

review_count 34->37 (+3), test_count 4->7 (+3), val_count unchanged at 30
(already at ceiling) — matches the goal's pre-annotation joint simulation
exactly (`decision-simulate-before-annotating`).
