---
goal: "Close the still-open gap named in the wiki's 11th pattern entry (PR #1373's own next_move): ReviewRecord._at_least_two_inputs_when_accepted only checks the *count* of input_annotation_ids, never that the referenced annotations actually form an independent pair (RFC 0012 SS9) -- so a non-independent-pair review can still be *written* and accepted through the store's public write_review API, even though release.py's _iaa_gates already excludes such a pair from IAA evidence at release time. Land a store-level guard (RED->GREEN TDD) that raises before persisting an accepted review whose inputs don't resolve to an independent pair, and open a reviewable PR."
id: "run-goals/20260909t152605z-do-the-best-useful-work-availab/goal-write-review-independence"
kind: "task-advance"
rationale: "Wiki entry 57 (segmenter_dataset audit, PR #1373) explicitly named this as unfixed: 'today's fix only stops it from being used as IAA evidence at release time' -- ReviewRecord._at_least_two_inputs_when_accepted still only checks count. The issue backlog (17 issues) is fully blocked/deprioritized per knowledge/backlog; the one open PR (#1353) is dependabot-only. This is the highest-confidence, most concretely-scoped lead available: a named, unaddressed correctness gap in a module this same loop has already audited twice (PR #1373, #1375)."
run: "runs/20260909T152605Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "tests/segmenter_dataset/test_store.py has a new RED (pre-fix)->GREEN (post-fix) test proving write_review raises NonIndependentReviewError for an accepted review whose two input annotations share a model_family or one is seeded from the other, while still allowing independent pairs and non-accepted statuses through unchanged; tests/segmenter_dataset/test_release.py's two release-gate tests exercising this same fixture shape are adapted (one to use a genuinely independent pair since its own intent -- unresolved-conflict detection -- is unrelated to independence; the other to write its already-invalid fixture by bypassing the new guard, proving release.py's _iaa_gates still holds as defense-in-depth). Full local suite (pytest, ruff check, ruff format --check) green, and a PR is opened."
type: "RunGoal"
---

# RunGoal
