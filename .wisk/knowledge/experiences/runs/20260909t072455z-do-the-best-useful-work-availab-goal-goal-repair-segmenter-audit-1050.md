---
goal: "Repair the 14 real documents scripts/segmenter_semantic_audit.py flags as collapsed (fundamentacao_legal/valor_condenacao anchors), per issue #1050's first work item, and fix the audit script to only check the latest annotation per document so repairs actually clear findings."
id: "run-goals/20260909t072455z-do-the-best-useful-work-availab/goal-repair-segmenter-audit-1050"
kind: "task-advance"
rationale: "Repo state check (wisk session next, then manual GitHub survey) found no eligible SessionType and no in-scope open PR/issue smaller than a multi-session initiative except this one: the semantic audit script already exists and reports 14 real findings against data/segmenter, issue #1047's critical path names #1050 as blocking further OPF training work, and #1050's own first bullet literally asks for this repair. TDD-able (RED test on the audit's stale-annotation bug), bounded to ~14 documents, and does not require GPU/IA credentials unlike the rest of #1047's backlog."
run: "runs/20260909T072455Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "scripts/segmenter_semantic_audit.py run against data/segmenter reports at most the one known/documented false-positive finding (down from 14), full pytest suite and ruff stay green, and a new regression test locks in that state."
type: "RunGoal"
---

# RunGoal
