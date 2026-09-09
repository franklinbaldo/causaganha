---
type: "RunOutcome"
id: "run-outcomes/20260909t112509z-do-the-best-useful-work-availab/outcome-final"
run: "runs/20260909T112509Z-do-the-best-useful-work-available-in-this-reposi"
result_state: "success"
work_status: "complete"
summary: "Wired release.py's no_unresolved_annotation_conflicts rigid gate (RFC 0012 §14) to real evidence instead of the hardcoded passed=True no-op flagged as unfinished by PR #1373's own next_move. Added _unresolved_conflicts(annotations, reviews): groups AnnotationRecords by document_id, detects pairwise label disagreement via frozenset equality, and treats a disagreement as resolved only when an accepted ReviewRecord's input_annotation_ids covers both annotation_ids. RED test (release succeeded despite a genuine unresolved conflict) -> GREEN (ReleaseBlockedError now names the gate; the same fixture builds once a covering accepted review exists, proving the gate is not failing-open). tests/segmenter_dataset: 241/241 green (was 240). Full repo suite (uv run pytest -q): all green, exit 0. ruff check + format --check clean. Opened PR #1375 and handoffs/handoff-pr-1375-awaiting-ci to track CI/merge."
next_move: "PR #1373's next_move named a second, still-open gap in the same annotator-independence family: ReviewRecord._at_least_two_inputs_when_accepted only checks the count of input_annotation_ids, never their independence -- so a non-independent-pair review (one seeded from the other, RFC 0012 §9's explicit non-example) can still be written and accepted, only stopped from being used as IAA evidence at release time (by the annotations_are_independent check PR #1373 already wired into _iaa_gates). That is the natural next slice in this family: extend ReviewRecord's validator (or add a companion check at the same layer) to call mechanical.annotations_are_independent over its own input_annotation_ids before accepting a review with only 2 inputs, resolving both against the AnnotationRecord store the validator doesn't currently have access to (a model_validator can't look records up -- likely needs a store-aware check at the write call site instead, mirroring how _iaa_gates does it, rather than inside the frozen pydantic model itself). Also still open from prior rounds: candidate_mining.py has zero real callers (issue #1050's 'mine real candidates for rare categories' bullet); preliminar remains the weakest category at support=10 (the floor). A future session should re-verify GitHub/issue/PR state first (per the wiki's standing invariant) rather than trust this summary alone -- in particular, confirm PR #1375's merge via the open handoff before starting new work."
goals_advanced: ["run-goals/20260909t112509z-do-the-best-useful-work-availab/goal-wire-annotation-conflict-gate"]
evidence: ["run-evidence/20260909t112509z-do-the-best-useful-work-availab/evidence-conflict-gate-red-green"]
checks: ["run-checks/20260909t112509z-do-the-best-useful-work-availab/check-full-suite-and-lint"]
experiences_recorded: []
---

# RunOutcome
