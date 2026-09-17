---
type: "RunDecision"
id: "run-decisions/20260917t032539z-do-the-best-useful-work-availab/decision-handoff-disposition"
run: "runs/20260917T032539Z-do-the-best-useful-work-available-in-this-reposi"
question: "handoff-issue-1471-ia-publish-pending asks to publish the reordered TJRO 2026 comunicacoes.parquet candidate to Internet Archive and prove a real read-back. IA_ACCESS_KEY/IA_SECRET_KEY remain absent in this container (7th consecutive round). What should this round do with the handoff's transferred goal?"
decision: "reframed"
rationale: "The handoff's core goal (publish + real Archive read-back for issue #1471) cannot be attempted without IA write credentials, which this environment does not have and a repository session cannot provision for itself -- re-diagnosing the same absence an 8th time would be pure churn (continuous-loop-operational-invariants.md warns against treating the issue backlog, or in this case a single stale handoff, as the whole work queue when it is blocked). The handoff itself remains valid and stays active/untouched for a future round with write access. This round instead pivots to issue #1050 (segmenter real-corpus growth, RFC 0012), the standing unblocked, high-continuity, evidence-backed lineage documented in knowledge/backlog/issue-1050.md across 17 prior batches (document_count 61->143 live-confirmed via scripts/segmenter_governance_status.py), which needs zero credentials and has a clear observable success_signal (document_count/val_ceiling/test_ceiling increase)."
alternatives: ["[\"Re-run the exact same IA-credential probe and end the round with no repository change -- rejected: 7 prior rounds already did this and the repo policy note (continuous-loop-operational-invariants.md) explicitly discourages treating a single blocked handoff as the whole work queue.\",\"Attempt to work around the missing credentials (e.g. hardcode/request new ones) -- rejected: out of scope for a repository session, and the handoff explicitly gates on real credentials being available, not a workaround.\"]"]
---

# RunDecision
