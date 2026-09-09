---
type: "RunEvidence"
id: "run-evidence/20260909t112509z-do-the-best-useful-work-availab/evidence-conflict-gate-red-green"
run: "runs/20260909T112509Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/segmenter_dataset/test_release.py::test_build_dataset_release_blocked_by_unresolved_annotation_conflict"
summary: "RED: new test built a train document with two AnnotationRecords whose labels disagree (differing cabecalho_fim offset) and no accepted review naming both; asserted ReleaseBlockedError names no_unresolved_annotation_conflicts -- failed with 'DID NOT RAISE ReleaseBlockedError' against the old hardcoded passed=True gate. GREEN after wiring release.py's new _unresolved_conflicts(annotations, reviews) helper (groups AnnotationRecords by document_id, itertools.combinations pairwise, frozenset(labels) equality to detect disagreement, resolved only if an accepted ReviewRecord's input_annotation_ids superset covers both annotation_ids) into the gate's passed/detail fields instead of the literal True. Same test then adds an accepted review covering both annotation_ids and asserts the release now succeeds with train count 11, proving the gate is not just failing-open. tests/segmenter_dataset/ full suite: 241/241 green (was 240). ruff check + format --check clean on both changed files."
goal: "run-goals/20260909t112509z-do-the-best-useful-work-availab/goal-wire-annotation-conflict-gate"
---

# RunEvidence
