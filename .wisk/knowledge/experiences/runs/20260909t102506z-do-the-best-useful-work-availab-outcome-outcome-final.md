---
type: "RunOutcome"
id: "run-outcomes/20260909t102506z-do-the-best-useful-work-availab/outcome-final"
run: "runs/20260909T102506Z-do-the-best-useful-work-available-in-this-reposi"
result_state: "success"
work_status: "complete"
summary: "Continued issue #1050 with an Explore-agent-dispatched audit of segmenter_dataset modules not yet covered by prior audit rounds. Found a genuine, previously-undetected gap: RFC 0012 section 5.3's annotator-independence invariant was declared (AnnotationRecord.is_independent_capable(), referencing a mechanical.annotations_are_independent that never existed) but never enforced anywhere -- release.py's _iaa_gates accepted any two annotations referenced by an accepted review as inter-annotator evidence with only a count check, so a review built from an annotation seeded from another annotation's own output could fabricate a near-1.0 IAA score and pass the rigid, non-waivable iaa_aggregate_floor gate. Fixed via RED (5 unit tests for the missing function; one release-level integration test proving the release currently succeeds when it should be blocked) -> GREEN (implemented annotations_are_independent; wired it into _iaa_gates's pair selection). tests/segmenter_dataset/ 140/140 green (was 122); full repo suite and ruff clean. Pushed to branch claude/exciting-mccarthy-x7apxk, opened PR #1373."
next_move: "PR #1373 needs CI confirmation and merge -- a follow-up round should verify green checks and merge, then archive the handoff this round records. Beyond that, the same audit surfaced two related, still-open gaps in the same independence-invariant family, deliberately left for a future round rather than widening this PR: (1) ReviewRecord._at_least_two_inputs_when_accepted only checks len(input_annotation_ids) >= 2, never the referenced AnnotationRecords' independence -- a store-level write path (e.g. SegmenterDatasetStore.write_review) could still persist a non-independent-pair review; today's fix only stops it from inflating IAA at release time, not from being written at all. (2) gates.py's no_unresolved_annotation_conflicts gate is hardcoded passed=True and never actually checks anything. Independently of that family, issue #1050's larger unstarted scope remains: candidate_mining.py exists and is tested but has zero callers/consumers (no script wires it to real, not-yet-annotated documents), and mining real candidates for preliminar (support=10, still the weakest category) plus scaling toward the 25/50/100+ learning-curve checkpoints is still all ahead."
goals_advanced: ["run-goals/20260909t102506z-do-the-best-useful-work-availab/goal-audit-segmenter-dataset"]
evidence: ["run-evidence/20260909t102506z-do-the-best-useful-work-availab/evidence-independence-red-green"]
checks: ["run-checks/20260909t102506z-do-the-best-useful-work-availab/check-full-suite-and-lint"]
experiences_recorded: []
---

# RunOutcome
