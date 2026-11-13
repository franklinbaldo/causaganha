---
type: AgentEvidence
id: "2026-09-26-exciting-mccarthy-sg2540-evidence-reviews-ingested"
run_id: "2026-09-26-exciting-mccarthy-sg2540"
goal_id: "2026-09-26-exciting-mccarthy-sg2540-goal-1051-test-split-adjudication"
kind: "runtime"
reference: "data/segmenter/reviews/{doc_6b9ee9d4f525b8442af4cbc20da41269,doc_c41321b105269252919a5d4d730800a2,doc_7e91843200b79e7467d0ae541ad9c6c8,doc_52ca8d9d94f86a8426e0e9c3c7ef158b}/*.xml"
summary: "4 accepted ReviewRecords written via scripts/adjudicate_segmenter_review.py. Post-ingestion, scripts/segmenter_governance_status.py: review_count 48->52, test_count 18->22 (val_count unchanged at 30, already at ceiling) -- exactly matching the pre-annotation joint simulation."
---

# Evidence: 4 reviews ingested, governance status advanced

```
$ uv run python scripts/segmenter_governance_status.py
{
  "document_count": 197,
  "annotation_count": 275,
  "review_count": 52,
  "train_eligible_count": 197,
  "evaluation_eligible_count": 52,
  "blocked_on_reviews": false,
  "val_count": 30,
  "test_count": 22,
  "val_ceiling_at_full_adjudication": 30,
  "test_ceiling_at_full_adjudication": 30,
  "meets_rfc_0012_split_floor": false,
  "corpus_scale_blocks_floor": false
}
```

`review_ids`: `rev_62d558029268198d131c9b897d783a21` (TRF4),
`rev_9769fd7a9505c3921a46dfddb4f16c74` (TJMS),
`rev_4616a12e302faecdcbde07afdce6ed26` (TJPI, second attempt after the
`long_anchor` fix), `rev_a2fbf57c6344ec3c95214030feedbeb4` (TJES). All
`status="accepted"`.

`meets_rfc_0012_split_floor` still `False` (need >=30/>=30, have
30/22 -- 8 more accepted test-moving reviews needed at current hash
ordering).
