---
type: "RunEvidence"
id: "run-evidence/20260926t132422z-do-the-best-useful-work-availab/evidence-reviews-ingested"
run: "runs/20260926T132422Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "data/segmenter/reviews/doc_3f6fbeed801469206bd017a34cec4d15/, data/segmenter/reviews/doc_6129fdd7ecf441fb4629fd2476197bfa/, data/segmenter/reviews/doc_e2986082e14face4a4120f6de20e2248/"
summary: "3 accepted ReviewRecords ingested (TJMS, TRF2, TRF2), each resolving a genuinely independent second annotation (model_family=prompt_subagents:haiku) against the document's existing first annotation (model_family=prompt_subagents:general-purpose). scripts/segmenter_governance_status.py: review_count 48->51, test_count 18->21 (val_count unchanged at 30, its ceiling), matching the pre-round live simulation exactly. RED test (assert 48>=51 failed) turned GREEN after ingestion. scripts/segmenter_semantic_audit.py: 6 findings, matching the pre-existing baseline (a fresh long_anchor finding on doc_e2986082's second annotation was caught mid-round and fixed by deleting+re-ingesting with a tight span before finalizing). uv run pytest -q tests/segmenter_dataset: all green. uv run pytest -q (full suite): exit 0, 1 pre-existing skip. uv run ruff check/format --check: clean, 462 files. uv run okf-parser check: conformant, 0 diagnostics."
goal: "run-goals/20260926t132422z-do-the-best-useful-work-availab/goal-1051-next-batch"
---

# RunEvidence
