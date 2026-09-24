---
type: "RunCheck"
id: "run-checks/20260920t142524z-do-the-best-useful-work-availab/verification-pr-1594-merged"
run: "runs/20260920T142524Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "git worktree add /tmp/wt-main origin/main; cd /tmp/wt-main; uv run python scripts/segmenter_governance_status.py"
result: "Live on merged main (0563b06, squash-merge of PR #1594): document_count=191, annotation_count=244, val_ceiling=test_ceiling=29 -- exactly matching PR #1594's own claimed final numbers (184->191 documents, 28->29 ceiling). No silent no-op or data loss from the merge. RFC 0012 Sec 5 item 4 floor (>=30/>=30) still not reachable at this corpus size, as PR #1594 itself already documented (corpus_scale_blocks_floor=true)."
status: "pass"
evidence: "run-evidence/20260920t142524z-do-the-best-useful-work-availab/evidence-pr-1594-merged"
goal: "run-goals/20260920t142524z-do-the-best-useful-work-availab/goal-land-ready-prs"
---

# RunCheck
