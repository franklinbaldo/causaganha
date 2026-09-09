---
goal: "Audit the segmenter_dataset library modules not yet covered by the wiki's audit-history (ontology, store, splits, release, gates, iaa, mechanical, model_eval, region_eval, opf_export, okf_markdown, provenance, dedup wiring) against their real call sites in scripts/ and tests/, following issue #1050's still-open acceptance criteria (provenance completeness, dedup/leakage prevention across splits, class-support reporting). Find and fix one genuine correctness bug via RED->GREEN TDD, or make direct forward progress on an unstarted #1050 work item if no bug is found, and land it as a reviewable PR."
id: "run-goals/20260909t102506z-do-the-best-useful-work-availab/goal-audit-segmenter-dataset"
kind: "task-advance"
rationale: "Issue backlog is fully blocked/deprioritized (17 open issues, all pre-existing roadmap items with no near-term actionable slice); the one open PR is dependabot-only. The wiki's own next_move points at #1050's remaining scope, and the established, repeatedly-successful pattern in this loop (10 prior root-cause families found this way) is auditing a not-yet-swept module against its real callers rather than reading code in isolation."
run: "runs/20260909T102506Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "A PR is opened (or an existing one advanced to green/merged) containing a RED test that fails against the pre-fix code and passes after the fix, OR a wired, tested forward-progress contribution to one of #1050's unstarted bullets, with the full local test/lint suite green."
type: "RunGoal"
---

# RunGoal
