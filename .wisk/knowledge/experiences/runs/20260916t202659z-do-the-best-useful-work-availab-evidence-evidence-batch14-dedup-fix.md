---
type: "RunEvidence"
id: "run-evidence/20260916t202659z-do-the-best-useful-work-availab/evidence-batch14-dedup-fix"
run: "runs/20260916T202659Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "knowledge/backlog/issue-1050.md; tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch14_corpus_growth; docs/planning/evidence/segmenter-djen-sample-batch14-candidates.json"
summary: "RED: main (bee868e) document_count=123, missing TJPI(d6ee41ce)/TRF5(dfbd4832)/TST(fe3392b2) hashes. PR #1567 (branch claude/exciting-mccarthy-eoci0w) was opened against a stale pre-batch13 base and re-selected the exact same 5 candidates batch13 (PR #1565) had already ingested -- a real merge conflict plus a hidden defect: TJSE/578949084 got a second, differently-transcribed document under a different doc_id (would double-count one real document under two source hashes), TJRS/458637070 got a redundant second annotation on the same already-existing document. GREEN: resolved in a worktree, dropped the duplicate TJSE doc+annotation and the redundant TJRS annotation, kept only the 3 net-new documents (TJPI/TRF5/TST), renumbered evidence files batch13->batch14, split the governance test into an unchanged batch13 assertion plus a new test_real_store_reflects_batch14_corpus_growth (document_count==126, verified live). Push to origin/claude/exciting-mccarthy-eoci0w failed HTTP 403 (no access to another session's branch); re-applied the identical fix as a patch onto this session's own branch (claude/exciting-mccarthy-7bkhq5) rebased on current main instead."
goal: "goal-fix-pr1567-collision"
---

# RunEvidence
