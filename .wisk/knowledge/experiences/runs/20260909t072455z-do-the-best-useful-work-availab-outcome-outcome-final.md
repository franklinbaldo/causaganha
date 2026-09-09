---
type: "RunOutcome"
id: "run-outcomes/20260909t072455z-do-the-best-useful-work-availab/outcome-final"
run: "runs/20260909T072455Z-do-the-best-useful-work-available-in-this-reposi"
result_state: "success"
work_status: "complete"
summary: "Repaired 13 of the 14 real documents scripts/segmenter_semantic_audit.py flagged as collapsed (fundamentacao_legal/valor_condenacao), per issue #1050's first work item; the 14th was reviewed and confirmed as a genuine heuristic false positive, documented rather than force-fixed. Also fixed find_anti_patterns() to audit only the latest annotation per document (it previously re-flagged superseded, already-repaired annotations forever), via RED (regression test on a synthetic fixture) -> GREEN. Added a real-store regression test locking in the 14->1 result. Full pytest suite, ruff check/format all green. Opened PR #1367 (https://github.com/franklinbaldo/causaganha/pull/1367)."
next_move: "PR #1367 is open and needs CI/merge confirmation by a follow-up round. #1050 itself remains open beyond this slice — its other bullets (mining rare-category documents, scaling to 25/50/100+ train docs, versioning the annotation prompt/guideline, class-support reporting) are unstarted and are the natural next advance once #1367 lands."
goals_advanced: ["run-goals/20260909t072455z-do-the-best-useful-work-availab/goal-repair-segmenter-audit-1050"]
evidence: ["run-evidence/20260909t072455z-do-the-best-useful-work-availab/evidence-repair-run-observed"]
checks: ["run-checks/20260909t072455z-do-the-best-useful-work-availab/check-full-suite-lint-audit-green"]
experiences_recorded: []
---

# RunOutcome
