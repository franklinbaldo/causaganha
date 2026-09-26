---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-6m3b2b-check-governance-status-post-merge-local"
run_id: "2026-09-26-exciting-mccarthy-6m3b2b"
procedure: "uv run python scripts/segmenter_governance_status.py (run against the local merge of origin/main into PR #1678's branch, before discovering the concurrent duplicate fix)"
result: "document_count=197, annotation_count=271, review_count=48, val_count=30 (ceiling), test_count=18 (of the RFC 0012 Sec 5 item 4 floor of 30), meets_rfc_0012_split_floor=False, corpus_scale_blocks_floor=False"
evidence_id: "2026-09-26-exciting-mccarthy-6m3b2b-evidence-1678-reconciled-concurrently"
---

# Check: governance status pós-merge local de PR #1678
