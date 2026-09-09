---
goal: "Wire release.py's no_unresolved_annotation_conflicts rigid gate (RFC 0012 §14) to real evidence instead of its hardcoded passed=True no-op, continuing PR #1373's own explicitly deferred next_move."
id: "run-goals/20260909t112509z-do-the-best-useful-work-availab/goal-wire-annotation-conflict-gate"
kind: "task-advance"
rationale: "17-issue backlog re-verified still fully blocked/deprioritized (same set as every prior round); the only open PR is a Dependabot devDependency bump, not agent work to resume; no active Wisk handoff. The prior round's (20260909T102506Z, PR #1373) own next_move explicitly named this gate as unfinished: 'gates.py's no_unresolved_annotation_conflicts gate is hardcoded passed=True, never checking anything'. RFC 0012 §14 lists 'nenhum conflito de anotação não resolvido' as its own rigid, non-waivable gate, distinct from val_test_independently_adjudicated -- so a document with two annotation records whose labels disagree and no accepted review naming both annotation_ids currently passes release with zero evidence, exactly the kind of unenforced-invariant hazard the wiki's growing pattern family (11 prior instances) warns about."
run: "runs/20260909T112509Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "release.build_dataset_release raises ReleaseBlockedError naming no_unresolved_annotation_conflicts for a fixture with two disagreeing annotation records and no covering accepted review; the same fixture with an accepted review naming both annotation_ids builds successfully. New RED test proves the gap before the fix, GREEN after; full segmenter_dataset suite stays green."
type: "RunGoal"
---

# RunGoal
