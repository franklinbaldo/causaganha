---
type: "RunEvidence"
id: "run-evidence/20260909t102506z-do-the-best-useful-work-availab/evidence-independence-red-green"
run: "runs/20260909T102506Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/segmenter_dataset/test_mechanical.py, tests/segmenter_dataset/test_release.py, src/segmenter_dataset/mechanical.py, src/segmenter_dataset/release.py"
summary: "Found (via a dispatched Explore-agent audit, then independently re-verified line-by-line) that RFC 0012 section 5.3's annotator-independence invariant was never enforced: AnnotationRecord.is_independent_capable() in schemas.py references mechanical.annotations_are_independent, which did not exist anywhere in the repo (grep confirmed), and release.py's _iaa_gates picked inputs[0]/inputs[1] from a review's referenced annotations with zero independence check, only a count check. Concretely: a review built from an annotation and a second annotation seeded from the first's own output (a correction pass, per RFC 0012 section 9's own non-example) would compute a near-1.0 IAA and pass the rigid, non-waivable iaa_aggregate_floor gate. RED: added 5 unit tests for the missing function (import error) and one release-level integration test (test_build_dataset_release_blocked_when_val_pairs_are_not_independent) asserting ReleaseBlockedError citing iaa_aggregate_floor for an all-non-independent val split -- confirmed it currently DID NOT RAISE. GREEN: implemented mechanical.annotations_are_independent (both unseeded + distinct model_family) and wired it into release.py's pairs_for as an additional skip condition alongside the existing insufficient-inputs check. Full tests/segmenter_dataset/ suite: 140/140 green (up from 122). Full repo suite: all passing, ruff clean."
goal: "run-goals/20260909t102506z-do-the-best-useful-work-availab/goal-audit-segmenter-dataset"
---

# RunEvidence
