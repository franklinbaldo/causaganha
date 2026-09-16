---
goal: "Fix open PR #1567 (segmenter #1050 batch, branch claude/exciting-mccarthy-eoci0w): it was opened against a pre-batch13 base and independently re-selected the exact same 5 lowest-store_count candidates as the just-merged batch13 (PR #1565), producing a real merge conflict plus a hidden duplicate-document/duplicate-annotation defect for TJSE/578949084 and TJRS/458637070."
id: "run-goals/20260916t202659z-do-the-best-useful-work-availab/goal-fix-pr1567-collision"
kind: "task-advance"
rationale: "PRIORIZE CONTINUIDADE: an open PR from this same #1050 lineage is the best available advance for CausaGanha this round, and its merge conflict masks a real data-integrity defect (a second, differently-transcribed TJSE document would double-count one real document under two hashes if merged as-is) that must be fixed before merge, not just mechanically resolved."
run: "runs/20260916T202659Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "PR #1567's branch is merged with main, the store correctly has document_count==126 with no duplicate document/annotation, the corpus-growth test suite passes (test_real_store_reflects_batch13_corpus_growth unchanged + new test_real_store_reflects_batch14_corpus_growth green), and the fix is pushed to origin/claude/exciting-mccarthy-eoci0w."
type: "RunGoal"
---

# RunGoal
