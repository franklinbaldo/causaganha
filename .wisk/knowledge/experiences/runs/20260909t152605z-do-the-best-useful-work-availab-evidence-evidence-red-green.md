---
type: "RunEvidence"
id: "run-evidence/20260909t152605z-do-the-best-useful-work-availab/evidence-red-green"
run: "runs/20260909T152605Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "src/segmenter_dataset/store.py (NonIndependentReviewError, SegmenterDatasetStore._require_independent_inputs, write_review); tests/segmenter_dataset/test_store.py (3 new tests); tests/segmenter_dataset/test_release.py (2 fixtures adapted)"
summary: "RED: added tests/segmenter_dataset/test_store.py::test_write_review_rejects_accepted_review_from_same_family_annotations and ::test_write_review_rejects_accepted_review_from_seeded_annotation against pre-fix store.py -- collection failed with ImportError: cannot import name 'NonIndependentReviewError' from 'segmenter_dataset.store' (it didn't exist yet). GREEN after adding NonIndependentReviewError and wiring write_review to call a new _require_independent_inputs helper (mirrors release.py's _iaa_gates: resolves input_annotation_ids against the store's own list_annotations for that document, requires >=2 resolvable and mechanical.annotations_are_independent(inputs[0], inputs[1])) before persisting any review with status=='accepted'; a third new test confirms a non-independent pair is still allowed through for a non-accepted (e.g. 'pending') status. Two pre-existing tests in test_release.py had fixtures that happened to rely on writing a non-independent-pair accepted review as setup for unrelated release-gate assertions (same default model_family for both annotators in the unresolved-conflict test; an explicitly seeded pair in the not-independent-val-pairs test) -- adapted the first to use distinct model families (its own intent is conflict-resolution, not independence) and the second to write its fixture via a new _write_review_bypassing_independence_guard test helper (direct XML write, simulating legacy/non-store-API data) so it still proves release.py's _iaa_gates holds as defense-in-depth now that the store-level guard makes that state unreachable through the public API."
goal: "run-goals/20260909t152605z-do-the-best-useful-work-availab/goal-write-review-independence"
---

# RunEvidence
