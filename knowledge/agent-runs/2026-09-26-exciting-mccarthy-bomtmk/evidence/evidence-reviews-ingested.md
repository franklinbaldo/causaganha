---
type: AgentEvidence
id: "2026-09-26-exciting-mccarthy-bomtmk-evidence-reviews-ingested"
run_id: "2026-09-26-exciting-mccarthy-bomtmk"
goal_id: "2026-09-26-exciting-mccarthy-bomtmk-goal-1051-test-split-adjudication"
kind: "runtime"
reference: "scripts/adjudicate_segmenter_review.py x3, scripts/segmenter_governance_status.py"
summary: "3 new accepted ReviewRecords written (rev_a88a6be36d3713a914d115f737e9a0ca/TRF2, rev_19825af5f4d62945541e5e4d0c007035/TJES, rev_17b8b3de07c1e2643aff8bc8c08ee5d8/TJSE). Post-ingestion scripts/segmenter_governance_status.py: document_count=197 (unchanged), annotation_count 260->263, review_count 37->40, val_count=30 (unchanged, already at ceiling), test_count 7->10 -- exactly matching the pre-annotation joint simulation (decision-simulate-before-annotating)."
---

# Evidence: 3 reviews ingested, governance status confirms test_count 7->10

```
$ uv run python scripts/adjudicate_segmenter_review.py ... doc_8904b2884e6177d2b61fd7462ce7539d ...
Wrote review rev_a88a6be36d3713a914d115f737e9a0ca for doc_8904b2884e6177d2b61fd7462ce7539d

$ uv run python scripts/adjudicate_segmenter_review.py ... doc_6b29f96e41baeb5405c87bd09fb38d3d ...
Wrote review rev_19825af5f4d62945541e5e4d0c007035 for doc_6b29f96e41baeb5405c87bd09fb38d3d

$ uv run python scripts/adjudicate_segmenter_review.py ... doc_de65a409f2156cc18d43f96fa35347fc ...
Wrote review rev_17b8b3de07c1e2643aff8bc8c08ee5d8 for doc_de65a409f2156cc18d43f96fa35347fc

$ uv run python scripts/segmenter_governance_status.py
{
  "document_count": 197,
  "annotation_count": 263,
  "review_count": 40,
  "train_eligible_count": 197,
  "evaluation_eligible_count": 40,
  "blocked_on_reviews": false,
  "val_count": 30,
  "test_count": 10,
  "val_ceiling_at_full_adjudication": 30,
  "test_ceiling_at_full_adjudication": 30,
  "meets_rfc_0012_split_floor": false,
  "corpus_scale_blocks_floor": false
}
```

`git status --short data/segmenter` confirms exactly 3 new annotation
files and 3 new review directories, no other document touched.
